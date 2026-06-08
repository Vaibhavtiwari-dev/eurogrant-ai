from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app import models
from app.main import app

client = TestClient(app)


# The patch targets used throughout — defined once for consistency
CELERY_DELAY_PATH = "app.routers.proposals.generate_proposal_task.delay"
OPENAI_CLIENT_PATH = "app.services.proposal_gen._get_openai_client"


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
