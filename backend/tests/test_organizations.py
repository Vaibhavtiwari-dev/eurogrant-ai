import pytest
from app import models, schemas


def test_get_my_organization(authenticated_client, test_user):
    response = authenticated_client.get("/api/v1/organizations/me")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == test_user.organization_id
    assert "name" in data
    assert "subscription_tier" in data


def test_update_my_organization(authenticated_client, test_user, db_session):
    # Sanity check pre-update
    pre = db_session.query(models.Organization).filter(
        models.Organization.id == test_user.organization_id
    ).first()
    assert pre is not None

    response = authenticated_client.put(
        "/api/v1/organizations/me",
        json={
            "sector": "EnergyTech",
            "headcount_range": "11-50",
            "revenue_tier": "1M-10M",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["sector"] == "EnergyTech"
    assert data["headcount_range"] == "11-50"
    assert data["revenue_tier"] == "1M-10M"

    # The DB row should reflect the new values
    db_session.expire_all()
    post = db_session.query(models.Organization).filter(
        models.Organization.id == test_user.organization_id
    ).first()
    assert post.sector == "EnergyTech"


def test_update_my_organization_partial(authenticated_client, test_user, db_session):
    # PUT with only one field should leave the others untouched
    response = authenticated_client.put(
        "/api/v1/organizations/me",
        json={"match_threshold": 0.85},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["match_threshold"] == 0.85


def test_update_my_organization_validates_threshold(authenticated_client, test_user):
    # Pydantic schema constrains match_threshold to 0..1
    response = authenticated_client.put(
        "/api/v1/organizations/me",
        json={"match_threshold": 1.5},
    )
    assert response.status_code == 422


def test_get_dashboard_overview_empty(authenticated_client, test_user):
    # No documents uploaded yet — pipelines and hot_matches should be empty
    response = authenticated_client.get("/api/v1/organizations/dashboard-overview")
    assert response.status_code == 200
    data = response.json()
    assert "stats" in data
    assert data["stats"]["active_high_matches"] == 0
    assert data["pipelines"] == []
    assert data["hot_matches"] == []


def test_get_dashboard_overview_with_documents(authenticated_client, test_user, db_session):
    # Insert a couple of processed documents
    for i in range(3):
        doc = models.CompanyDocument(
            organization_id=test_user.organization_id,
            file_name=f"doc_{i}.pdf",
            s3_key=f"org_{test_user.organization_id}/doc_{i}.pdf",
            content_type="application/pdf",
            status=models.DocumentStatus.PROCESSED,
        )
        db_session.add(doc)
    db_session.commit()

    response = authenticated_client.get("/api/v1/organizations/dashboard-overview")
    assert response.status_code == 200
    data = response.json()
    assert data["stats"]["active_high_matches"] == 3
    # When there are docs, placeholder pipelines + hot_matches surface
    assert len(data["pipelines"]) >= 1
    assert len(data["hot_matches"]) >= 1
