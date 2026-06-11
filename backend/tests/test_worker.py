import json
import uuid
from contextlib import contextmanager
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def mock_s3_service():
    with patch("app.services.s3.s3_service.get_fileobj", return_value=b"fake content"):
        yield


@pytest.fixture
def mock_extraction():
    mock_text = MagicMock(return_value="Extracted text")
    mock_redact = MagicMock(return_value="Safe text")
    with (
        patch("app.services.extraction.extraction_service.extract_text", mock_text),
        patch("app.services.extraction.redact_pii", mock_redact),
    ):
        yield {"text": mock_text, "redact": mock_redact}


def test_process_company_document_success(db_session, mock_s3_service, mock_extraction):
    from app import models
    from app.worker import process_company_document

    org = models.Organization(name="Worker Org")
    db_session.add(org)
    db_session.commit()

    doc = models.CompanyDocument(
        organization_id=org.id,
        file_name="test.pdf",
        s3_key="key",
        content_type="application/pdf",
        status=models.DocumentStatus.PENDING,
    )
    db_session.add(doc)
    db_session.commit()

    mock_vector = MagicMock()
    mock_extract = MagicMock()

    with (
        patch("app.services.vector_db.get_vector_service", return_value=mock_vector),
        patch("app.worker.extract_company_profile", mock_extract),
    ):
        process_company_document(doc.id)

        db_session.expire_all()
        updated_doc = (
            db_session.query(models.CompanyDocument)
            .filter(models.CompanyDocument.id == doc.id)
            .first()
        )
        assert updated_doc.status == models.DocumentStatus.PROCESSED
        assert mock_vector.upsert_text.called
        assert mock_extract.called


def test_extract_company_profile(db_session):
    from app import models
    from app.worker import extract_company_profile

    org = models.Organization(name="Profile Org")
    db_session.add(org)
    db_session.commit()

    mock_response = MagicMock()
    mock_response.choices[0].message.content = json.dumps(
        {
            "sector": "Tech",
            "headcount_range": "11-50",
            "revenue_tier": "1M-5M",
            "legal_entity_type": "GmbH",
            "countries_of_operation": ["Germany"],
            "core_technologies": ["Python"],
        }
    )

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response

    with patch("app.services.llm_client.get_openai_client", return_value=mock_client):
        extract_company_profile("Document text", org.id, db_session)

        db_session.expire_all()
        updated_org = (
            db_session.query(models.Organization).filter(models.Organization.id == org.id).first()
        )
        assert updated_org.sector == "Tech"
        assert updated_org.headcount_range == "11-50"
        assert updated_org.revenue_tier == "1M-5M"
        assert updated_org.legal_entity_type == "GmbH"


def _create_regeneration_section(db_session):
    from app import models

    suffix = uuid.uuid4().hex[:8]
    org = models.Organization(name=f"Regeneration Org {suffix}")
    grant = models.Grant(
        external_id=f"REGEN-WORKER-{suffix}",
        title="Regeneration",
        description="Worker test",
        deadline=datetime(2027, 1, 1, tzinfo=UTC),
    )
    db_session.add_all([org, grant])
    db_session.commit()
    proposal = models.Proposal(
        organization_id=org.id,
        grant_id=grant.id,
        status=models.ProposalStatus.COMPLETED,
    )
    db_session.add(proposal)
    db_session.commit()
    section = models.ProposalSection(
        proposal_id=proposal.id,
        section_key="impact",
        name="Impact",
        content_json={
            "type": "doc",
            "content": [
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": "Original"}],
                }
            ],
        },
        order=0,
        status=models.SectionStatus.GENERATING,
        generation_job_id="regen-job",
        generation_base_version=1,
        version=1,
    )
    db_session.add(section)
    db_session.commit()
    return proposal, section


def test_stale_section_regeneration_does_not_call_service(db_session):
    from app.worker import regenerate_proposal_section_task

    proposal, section = _create_regeneration_section(db_session)

    @contextmanager
    def test_scope():
        yield db_session

    service = MagicMock()
    with (
        patch("app.database.session_scope", test_scope),
        patch("app.services.proposal_gen.get_proposal_service", return_value=service),
    ):
        regenerate_proposal_section_task(proposal.id, section.id, "different-job", base_version=1)
    service.regenerate_section_content.assert_not_called()


def test_section_regeneration_updates_matching_version(db_session):
    from app import models
    from app.worker import regenerate_proposal_section_task

    proposal, section = _create_regeneration_section(db_session)

    @contextmanager
    def test_scope():
        yield db_session

    service = MagicMock()
    service.regenerate_section_content.return_value = {
        "type": "doc",
        "content": [
            {
                "type": "paragraph",
                "content": [{"type": "text", "text": "Regenerated"}],
            }
        ],
    }
    with (
        patch("app.database.session_scope", test_scope),
        patch("app.services.proposal_gen.get_proposal_service", return_value=service),
    ):
        regenerate_proposal_section_task(proposal.id, section.id, "regen-job", base_version=1)

    db_session.expire_all()
    updated = db_session.get(models.ProposalSection, section.id)
    assert updated.version == 2
    assert updated.status == models.SectionStatus.COMPLETED
    assert updated.generation_job_id is None
    assert db_session.get(models.Proposal, proposal.id).content == "## Impact\n\nRegenerated"
