from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app import models
from app.main import app

client = TestClient(app)


def _seed_grant(db_session) -> models.Grant:
    grant = models.Grant(
        external_id="INT-001",
        title="Climate Resilience Innovation Grant",
        description="Funding for climate change adaptation and mitigation projects.",
        deadline=datetime(2026, 9, 1, 17, 0, tzinfo=UTC),
        funding_range="€100,000 - €500,000",
        eligibility_criteria="EU-registered SMEs working on climate technology",
        source_url="https://example.com/int-grant",
        sector_tags='["GreenTech", "Climate"]',
    )
    db_session.add(grant)
    db_session.commit()
    return grant


def test_grants_search_requires_authentication():
    """An unauthenticated search must be rejected with 401, not served."""
    response = client.post("/api/v1/grants/search", json={"query": "climate change"})
    assert response.status_code == 401


def test_grants_search_returns_matching_grant(db_session, authenticated_client):
    """End-to-end: an authenticated query flows through routing, DB, and back."""
    _seed_grant(db_session)

    response = authenticated_client.post(
        "/api/v1/grants/search",
        json={"query": "climate", "limit": 10},
    )

    assert response.status_code == 200
    data = response.json()
    assert any(g["title"] == "Climate Resilience Innovation Grant" for g in data)
