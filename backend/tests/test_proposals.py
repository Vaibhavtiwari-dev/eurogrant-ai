import json
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app import models
from app.main import app

client = TestClient(app)


# The patch targets used throughout — defined once for consistency
CELERY_DELAY_PATH = "app.routers.proposals.generate_proposal_task.delay"
OPENAI_CLIENT_PATH = "app.services.proposal_gen.get_openai_client"


# Helper for often-used patching kwargs
def _patch_openai():
    return patch(OPENAI_CLIENT_PATH, create=True)


# ---------------------------------------------------------------------------
# Router tests — POST /proposals
# ---------------------------------------------------------------------------


def test_create_proposal_unauthorized():
    """POST /api/v1/proposals/ without auth returns 401."""
    response = client.post("/api/v1/proposals/", json={"grant_id": 1})
    assert response.status_code == 401


def test_create_proposal_success(db_session, authenticated_client, test_user):
    """POST /api/v1/proposals/ queues generation and returns 202."""
    # Arrange: create a grant
    grant = models.Grant(
        external_id="PH10-001",
        title="Phase 10 Test Grant",
        description="A grant to test proposal generation.",
        deadline=datetime(2027, 1, 1, tzinfo=UTC),
        funding_range="€10,000 - €50,000",
        eligibility_criteria="SMEs",
        source_url="https://example.com/ph10",
        sector_tags='["Test"]',
    )
    db_session.add(grant)
    db_session.commit()

    # Mock the Celery task so we don't actually run it
    with patch(CELERY_DELAY_PATH) as mock_delay:
        response = authenticated_client.post(
            "/api/v1/proposals/",
            json={"grant_id": grant.id},
        )
        assert response.status_code == 202, response.text
        data = response.json()
        assert data["grant_id"] == grant.id
        assert data["organization_id"] == test_user.organization_id
        assert data["status"] == "pending"
        assert data["content"] is None
        assert "id" in data

        # Celery task was dispatched
        mock_delay.assert_called_once()
        # The proposal id is the first (and only) positional argument
        args, _ = mock_delay.call_args
        assert args[0] == data["id"]


def test_create_proposal_grant_not_found(authenticated_client):
    """POST /api/v1/proposals/ with a non-existent grant returns 404."""
    response = authenticated_client.post(
        "/api/v1/proposals/",
        json={"grant_id": 99999},
    )
    assert response.status_code == 404


def test_create_proposal_usage_limit(db_session, authenticated_client, test_user):
    """POST /api/v1/proposals/ returns 403 when the monthly limit is exceeded."""
    grant = models.Grant(
        external_id="PH10-LIMIT",
        title="Limit Test Grant",
        description="Testing usage limits.",
        deadline=datetime(2027, 2, 1, tzinfo=UTC),
        funding_range="€5,000",
        eligibility_criteria="SMEs",
        source_url="https://example.com/limit",
        sector_tags='["Test"]',
    )
    db_session.add(grant)
    db_session.commit()
    db_session.flush()

    # Growth tier = 5/month. Create 5 proposals to hit the limit.
    for _i in range(5):
        p = models.Proposal(
            organization_id=test_user.organization_id,
            grant_id=grant.id,
            status=models.ProposalStatus.COMPLETED,
        )
        db_session.add(p)
    db_session.commit()

    response = authenticated_client.post(
        "/api/v1/proposals/",
        json={"grant_id": grant.id},
    )
    assert response.status_code == 403, response.text
    assert "USAGE_LIMIT" in response.text


def test_create_proposal_usage_limit_agency_unlimited(db_session, authenticated_client, test_user):
    """Agency-tier organisations have no monthly limit."""
    # Bump the org to agency
    org = (
        db_session.query(models.Organization)
        .filter(models.Organization.id == test_user.organization_id)
        .first()
    )
    org.subscription_tier = "agency"
    db_session.commit()

    grant = models.Grant(
        external_id="PH10-AGENCY",
        title="Agency Grant",
        description="Unlimited proposals for agency tier.",
        deadline=datetime(2027, 3, 1, tzinfo=UTC),
        funding_range="€100,000",
        eligibility_criteria="SMEs",
        source_url="https://example.com/agency",
        sector_tags='["Test"]',
    )
    db_session.add(grant)
    db_session.commit()

    with patch(CELERY_DELAY_PATH) as mock_delay:
        response = authenticated_client.post(
            "/api/v1/proposals/",
            json={"grant_id": grant.id},
        )
        assert response.status_code == 202, response.text
        mock_delay.assert_called_once()


# ---------------------------------------------------------------------------
# Router tests — GET /proposals
# ---------------------------------------------------------------------------


def test_list_proposals_unauthorized():
    """GET /api/v1/proposals/ without auth returns 401."""
    response = client.get("/api/v1/proposals/")
    assert response.status_code == 401


def test_list_proposals(db_session, authenticated_client, test_user):
    """GET /api/v1/proposals/ returns only the current org's proposals."""
    grant = models.Grant(
        external_id="PH10-LIST",
        title="List Test Grant",
        description="Testing proposal listing.",
        deadline=datetime(2027, 4, 1, tzinfo=UTC),
        funding_range="€10,000",
        eligibility_criteria="SMEs",
        source_url="https://example.com/list",
        sector_tags='["Test"]',
    )
    db_session.add(grant)
    db_session.commit()

    # Create two proposals for the test org
    for i in range(2):
        p = models.Proposal(
            organization_id=test_user.organization_id,
            grant_id=grant.id,
            status=models.ProposalStatus.COMPLETED,
            content=f"Draft {i}",
            compatibility_score=0.8 + i * 0.1,
        )
        db_session.add(p)
    db_session.commit()

    response = authenticated_client.get("/api/v1/proposals/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    scores = {p["compatibility_score"] for p in data}
    assert scores == {0.8, 0.9}


def test_list_proposals_scoped_to_org(db_session, authenticated_client, test_user):
    """GET /api/v1/proposals/ does not leak proposals from other orgs."""
    grant = models.Grant(
        external_id="PH10-SCOPE",
        title="Scope Test Grant",
        description="Testing org scoping.",
        deadline=datetime(2027, 5, 1, tzinfo=UTC),
        funding_range="€10,000",
        eligibility_criteria="SMEs",
        source_url="https://example.com/scope",
        sector_tags='["Test"]',
    )
    db_session.add(grant)
    db_session.commit()

    # Proposal for *another* org
    other_org = models.Organization(name="Other Org PH10", subscription_tier="growth")
    db_session.add(other_org)
    db_session.commit()
    other_proposal = models.Proposal(
        organization_id=other_org.id,
        grant_id=grant.id,
        status=models.ProposalStatus.PENDING,
    )
    db_session.add(other_proposal)
    # Proposal for *our* org
    our_proposal = models.Proposal(
        organization_id=test_user.organization_id,
        grant_id=grant.id,
        status=models.ProposalStatus.COMPLETED,
        content="Our draft",
    )
    db_session.add(our_proposal)
    db_session.commit()

    response = authenticated_client.get("/api/v1/proposals/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == our_proposal.id


# ---------------------------------------------------------------------------
# Router tests — GET /proposals/{id}
# ---------------------------------------------------------------------------


def test_get_proposal(db_session, authenticated_client, test_user):
    """GET /api/v1/proposals/{id} returns a single proposal."""
    grant = models.Grant(
        external_id="PH10-GET",
        title="Get Test Grant",
        description="Testing single proposal retrieval.",
        deadline=datetime(2027, 6, 1, tzinfo=UTC),
        funding_range="€10,000",
        eligibility_criteria="SMEs",
        source_url="https://example.com/get",
        sector_tags='["Test"]',
    )
    db_session.add(grant)
    db_session.commit()

    proposal = models.Proposal(
        organization_id=test_user.organization_id,
        grant_id=grant.id,
        status=models.ProposalStatus.COMPLETED,
        content="Final draft content here.",
        compatibility_score=0.85,
    )
    db_session.add(proposal)
    db_session.commit()

    response = authenticated_client.get(f"/api/v1/proposals/{proposal.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == proposal.id
    assert data["content"] == "Final draft content here."
    assert data["compatibility_score"] == 0.85
    assert data["status"] == "completed"


def test_get_proposal_not_found(authenticated_client):
    """GET /api/v1/proposals/{id} returns 404 for a non-existent proposal."""
    response = authenticated_client.get("/api/v1/proposals/99999")
    assert response.status_code == 404


def test_get_proposal_wrong_org(db_session, authenticated_client, test_user):
    """GET /api/v1/proposals/{id} returns 404 for proposals from other orgs."""
    grant = models.Grant(
        external_id="PH10-WRONG",
        title="Wrong Org Test Grant",
        description="Testing org isolation for single proposal.",
        deadline=datetime(2027, 7, 1, tzinfo=UTC),
        funding_range="€10,000",
        eligibility_criteria="SMEs",
        source_url="https://example.com/wrong",
        sector_tags='["Test"]',
    )
    db_session.add(grant)
    db_session.commit()

    other_org = models.Organization(name="Other Org PH10 Wrong", subscription_tier="growth")
    db_session.add(other_org)
    db_session.commit()

    proposal = models.Proposal(
        organization_id=other_org.id,
        grant_id=grant.id,
        status=models.ProposalStatus.PENDING,
    )
    db_session.add(proposal)
    db_session.commit()

    response = authenticated_client.get(f"/api/v1/proposals/{proposal.id}")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Service tests — ProposalService.generate_initial_draft
# ---------------------------------------------------------------------------


def test_proposal_service_missing_grant(db_session):
    """ProposalService raises ValueError when the grant does not exist."""
    from app.services.proposal_gen import ProposalService

    service = ProposalService()
    with pytest.raises(ValueError, match="Grant with id 99999 not found"):
        service.generate_initial_draft(db=db_session, org_id=1, grant_id=99999)


def test_proposal_service_success(db_session, test_user):
    """ProposalService returns content and score when the LLM call succeeds."""
    from app.services.proposal_gen import ProposalService

    # Arrange: create grant + ensure org exists
    grant = models.Grant(
        external_id="PH10-SVC",
        title="Service Test Grant",
        description="A grant for testing the ProposalService.",
        deadline=datetime(2027, 8, 1, tzinfo=UTC),
        funding_range="€50,000",
        eligibility_criteria="SMEs with AI focus",
        scoring_rubric="1. Innovation (30pts)\n2. Impact (30pts)\n3. Team (20pts)\n4. Budget (20pts)",
        source_url="https://example.com/svc",
        sector_tags='["AI", "Test"]',
    )
    db_session.add(grant)
    db_session.commit()

    service = ProposalService()

    # Mock the LLM call to avoid actual API charges
    mock_content = (
        '{"proposal": "# Proposal\\n\\n## 1. Innovation\\nWe use AI to...\\n\\n'
        "## 2. Impact\\nExpected outcomes...\\n\\n"
        '## 3. Budget\\nTotal: €50,000", "compatibility_score": 0.82}'
    )

    with _patch_openai() as mock_get_client:
        mock_client = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = mock_content
        mock_client.chat.completions.create.return_value = MagicMock(choices=[mock_choice])
        mock_get_client.return_value = mock_client

        content, score = service.generate_initial_draft(
            db=db_session,
            org_id=test_user.organization_id,
            grant_id=grant.id,
        )

    assert score == 0.82
    assert "Innovation" in content
    assert "Impact" in content
    assert mock_client.chat.completions.create.called


def test_proposal_service_llm_failure(db_session, test_user):
    """ProposalService raises RuntimeError when the LLM fails."""
    from app.services.proposal_gen import ProposalService

    grant = models.Grant(
        external_id="PH10-FAIL",
        title="Failure Test Grant",
        description="Testing LLM failure handling.",
        deadline=datetime(2027, 9, 1, tzinfo=UTC),
        funding_range="€10,000",
        eligibility_criteria="SMEs",
        source_url="https://example.com/fail",
        sector_tags='["Test"]',
    )
    db_session.add(grant)
    db_session.commit()

    service = ProposalService()

    with _patch_openai() as mock_get_client:
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = Exception("API timeout")
        mock_get_client.return_value = mock_client

        with pytest.raises(RuntimeError, match="LLM proposal generation failed"):
            service.generate_initial_draft(
                db=db_session,
                org_id=test_user.organization_id,
                grant_id=grant.id,
            )


def _create_sectioned_proposal(db_session, test_user):
    grant = models.Grant(
        external_id=f"SECTION-{test_user.id}",
        title="Section API Grant",
        description="Section API tests.",
        deadline=datetime(2027, 10, 1, tzinfo=UTC),
    )
    db_session.add(grant)
    db_session.commit()
    proposal = models.Proposal(
        organization_id=test_user.organization_id,
        grant_id=grant.id,
        status=models.ProposalStatus.COMPLETED,
    )
    db_session.add(proposal)
    db_session.commit()
    section = models.ProposalSection(
        proposal_id=proposal.id,
        section_key="summary",
        name="Executive Summary",
        content_json={
            "type": "doc",
            "content": [
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": "Initial"}],
                }
            ],
        },
        order=0,
        status=models.SectionStatus.COMPLETED,
        version=1,
    )
    db_session.add(section)
    db_session.commit()
    return proposal, section


def test_viewer_cannot_create_proposal(db_session, authenticated_client, test_user):
    test_user.role = models.RoleEnum.VIEWER
    db_session.commit()
    response = authenticated_client.post("/api/v1/proposals/", json={"grant_id": 1})
    assert response.status_code == 403


def test_viewer_can_read_sections(db_session, authenticated_client, test_user):
    proposal, section = _create_sectioned_proposal(db_session, test_user)
    test_user.role = models.RoleEnum.VIEWER
    db_session.commit()
    response = authenticated_client.get(f"/api/v1/proposals/{proposal.id}/sections")
    assert response.status_code == 200
    assert response.json()[0]["id"] == section.id
    assert "generation_job_id" not in response.json()[0]


def test_viewer_cannot_edit_section(db_session, authenticated_client, test_user):
    proposal, section = _create_sectioned_proposal(db_session, test_user)
    test_user.role = models.RoleEnum.VIEWER
    db_session.commit()
    response = authenticated_client.patch(
        f"/api/v1/proposals/{proposal.id}/sections/{section.id}",
        json={"content_json": {"type": "doc"}, "expected_version": 1},
    )
    assert response.status_code == 403


def test_update_section_rebuilds_snapshot(db_session, authenticated_client, test_user):
    proposal, section = _create_sectioned_proposal(db_session, test_user)
    document = {
        "type": "doc",
        "content": [
            {
                "type": "paragraph",
                "content": [{"type": "text", "text": "Updated safely"}],
            }
        ],
    }
    response = authenticated_client.patch(
        f"/api/v1/proposals/{proposal.id}/sections/{section.id}",
        json={"content_json": document, "expected_version": 1},
    )
    assert response.status_code == 200, response.text
    assert response.json()["version"] == 2
    db_session.expire_all()
    updated = db_session.get(models.Proposal, proposal.id)
    assert updated.content == "## Executive Summary\n\nUpdated safely"


def test_stale_update_returns_conflict(db_session, authenticated_client, test_user):
    proposal, section = _create_sectioned_proposal(db_session, test_user)
    response = authenticated_client.patch(
        f"/api/v1/proposals/{proposal.id}/sections/{section.id}",
        json={"content_json": {"type": "doc"}, "expected_version": 99},
    )
    assert response.status_code == 409
    assert "VERSION_CONFLICT" in response.text
    assert response.json()["detail"]["error"]["details"]["current_version"] == 1


def test_unsafe_section_content_is_rejected(db_session, authenticated_client, test_user):
    proposal, section = _create_sectioned_proposal(db_session, test_user)
    response = authenticated_client.patch(
        f"/api/v1/proposals/{proposal.id}/sections/{section.id}",
        json={
            "content_json": {
                "type": "doc",
                "content": [
                    {
                        "type": "paragraph",
                        "content": [
                            {
                                "type": "text",
                                "text": "click",
                                "marks": [
                                    {
                                        "type": "link",
                                        "attrs": {"href": "javascript:alert(1)"},
                                    }
                                ],
                            }
                        ],
                    }
                ],
            },
            "expected_version": 1,
        },
    )
    assert response.status_code == 422


def test_regenerate_queues_versioned_job(db_session, authenticated_client, test_user):
    proposal, section = _create_sectioned_proposal(db_session, test_user)
    with patch("app.routers.proposals.regenerate_proposal_section_task.delay") as mock_delay:
        response = authenticated_client.post(
            f"/api/v1/proposals/{proposal.id}/sections/{section.id}/regenerate",
            json={"expected_version": 1},
        )
    assert response.status_code == 202, response.text
    assert response.json()["status"] == "generating"
    args = mock_delay.call_args.args
    assert args[0] == proposal.id
    assert args[1] == section.id
    assert args[3] == 1


def test_stale_regenerate_returns_conflict(db_session, authenticated_client, test_user):
    proposal, section = _create_sectioned_proposal(db_session, test_user)
    response = authenticated_client.post(
        f"/api/v1/proposals/{proposal.id}/sections/{section.id}/regenerate",
        json={"expected_version": 99},
    )
    assert response.status_code == 409
    assert "VERSION_CONFLICT" in response.text


def test_regenerate_queue_failure_is_visible(db_session, authenticated_client, test_user):
    proposal, section = _create_sectioned_proposal(db_session, test_user)
    with patch(
        "app.routers.proposals.regenerate_proposal_section_task.delay",
        side_effect=RuntimeError("queue unavailable"),
    ):
        response = authenticated_client.post(
            f"/api/v1/proposals/{proposal.id}/sections/{section.id}/regenerate",
            json={"expected_version": 1},
        )
    assert response.status_code == 503
    db_session.expire_all()
    updated = db_session.get(models.ProposalSection, section.id)
    assert updated.status == models.SectionStatus.FAILED
    assert updated.last_error_code == "QUEUE_UNAVAILABLE"


def test_generate_sections_records_partial_failure(db_session, test_user):
    from app.services.proposal_gen import (
        ExtractedSection,
        ExtractedSectionList,
        ProposalService,
    )

    grant = models.Grant(
        external_id="MULTI-PARTIAL",
        title="Multi Section",
        description="Generate sections.",
        deadline=datetime(2027, 11, 1, tzinfo=UTC),
        scoring_rubric="Impact and implementation",
    )
    db_session.add(grant)
    db_session.commit()
    proposal = models.Proposal(
        organization_id=test_user.organization_id,
        grant_id=grant.id,
        status=models.ProposalStatus.PROCESSING,
        generation_job_id="job-partial",
    )
    db_session.add(proposal)
    db_session.commit()

    service = ProposalService()
    with (
        patch.object(service, "_build_context", return_value="Safe context"),
        patch.object(
            service,
            "_extract_sections_from_rubric",
            return_value=ExtractedSectionList(
                sections=[
                    ExtractedSection(name="Impact"),
                    ExtractedSection(name="Implementation"),
                ],
                compatibility_score=0.75,
            ),
        ),
        patch.object(
            service,
            "_generate_section_content",
            side_effect=["Measurable impact.", RuntimeError("transient")],
        ),
    ):
        result = service.generate_proposal_sections(db_session, proposal.id, "job-partial")

    assert result.completed == 1
    assert result.failed == 1
    sections = (
        db_session.query(models.ProposalSection)
        .filter(models.ProposalSection.proposal_id == proposal.id)
        .order_by(models.ProposalSection.order)
        .all()
    )
    assert [section.status for section in sections] == [
        models.SectionStatus.COMPLETED,
        models.SectionStatus.FAILED,
    ]
    assert proposal.content == "## Impact\n\nMeasurable impact."


def test_generate_sections_aborts_stale_job(db_session, test_user):
    from app.services.proposal_gen import ProposalService

    grant = models.Grant(
        external_id="MULTI-STALE",
        title="Stale Job",
        description="Do not generate.",
        deadline=datetime(2027, 12, 1, tzinfo=UTC),
    )
    db_session.add(grant)
    db_session.commit()
    proposal = models.Proposal(
        organization_id=test_user.organization_id,
        grant_id=grant.id,
        status=models.ProposalStatus.PROCESSING,
        generation_job_id="current-job",
    )
    db_session.add(proposal)
    db_session.commit()

    result = ProposalService().generate_proposal_sections(db_session, proposal.id, "stale-job")

    assert result.completed == 0
    assert result.failed == 0
    assert (
        db_session.query(models.ProposalSection)
        .filter(models.ProposalSection.proposal_id == proposal.id)
        .count()
        == 0
    )


def test_extract_sections_validates_and_caps_output():
    from app.services.proposal_gen import ProposalService

    service = ProposalService()
    grant = MagicMock()
    grant.id = 1
    grant.scoring_rubric = "Impact"
    grant.eligibility_criteria = "SMEs"
    raw = json.dumps(
        {
            "sections": [
                {"name": f"Section {index}", "description": "Test", "weight": 0.1}
                for index in range(10)
            ],
            "compatibility_score": 0.9,
        }
    )
    with patch.object(service, "_call_json_llm", return_value=raw):
        extracted = service._extract_sections_from_rubric(grant, "Context")
    assert len(extracted.sections) == 7
    assert extracted.compatibility_score == 0.9


def test_extract_sections_falls_back_on_invalid_output():
    from app.services.proposal_gen import ProposalService

    service = ProposalService()
    grant = MagicMock()
    grant.id = 1
    grant.scoring_rubric = "Impact"
    grant.eligibility_criteria = "SMEs"
    with patch.object(service, "_call_json_llm", return_value='{"sections": []}'):
        extracted = service._extract_sections_from_rubric(grant, "Context")
    assert extracted.sections[0].name == "Executive Summary"


def test_generate_section_content_uses_structured_response():
    from app.services.proposal_gen import ExtractedSection, ProposalService

    service = ProposalService()
    grant = MagicMock(title="Grant", description="Desc", eligibility_criteria="SMEs")
    org = MagicMock(name="Org")
    with patch.object(service, "_call_json_llm", return_value='{"content": "Generated body"}'):
        content = service._generate_section_content(
            ExtractedSection(name="Impact"), grant, org, "Context"
        )
    assert content == "Generated body"


def test_regenerate_section_content_uses_existing_definition(db_session, test_user):
    from app.services.proposal_gen import ProposalService

    proposal, section = _create_sectioned_proposal(db_session, test_user)
    service = ProposalService()
    with (
        patch.object(service, "_build_context", return_value="Context"),
        patch.object(
            service, "_generate_section_content", return_value="Regenerated body"
        ) as generate,
    ):
        document = service.regenerate_section_content(db_session, proposal.id, section.id)
    assert document["type"] == "doc"
    assert document["content"][0]["content"][0]["text"] == "Regenerated body"
    assert generate.call_args.args[0].name == section.name


def test_regenerate_missing_section_raises(db_session):
    from app.services.proposal_gen import ProposalService

    with pytest.raises(ValueError, match="not found"):
        ProposalService().regenerate_section_content(db_session, 999, 999)


def test_call_json_llm_handles_success_empty_and_failure():
    from app.services.proposal_gen import ProposalService

    service = ProposalService()
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value.choices[0].message.content = "{}"
    with patch("app.services.proposal_gen.get_openai_client", return_value=mock_client):
        assert (
            service._call_json_llm("model", "system", "user", max_tokens=10, temperature=0) == "{}"
        )

    mock_client.chat.completions.create.return_value.choices[0].message.content = None
    with (
        patch("app.services.proposal_gen.get_openai_client", return_value=mock_client),
        pytest.raises(RuntimeError, match="empty"),
    ):
        service._call_json_llm("model", "system", "user", max_tokens=10, temperature=0)

    mock_client.chat.completions.create.side_effect = Exception("secret upstream detail")
    with (
        patch("app.services.proposal_gen.get_openai_client", return_value=mock_client),
        pytest.raises(RuntimeError, match="LLM request failed"),
    ):
        service._call_json_llm("model", "system", "user", max_tokens=10, temperature=0)


def test_section_key_normalization_and_duplicate_suffix():
    from app.services.proposal_gen import ProposalService

    seen = {}
    assert ProposalService._unique_section_key("Impact & Scale", seen) == "impact_scale"
    assert ProposalService._unique_section_key("Impact & Scale", seen) == "impact_scale_2"
