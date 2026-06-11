import uuid
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def mock_auth_passwords():
    with (
        patch("app.auth.get_password_hash") as mock_hash,
        patch("app.auth.verify_password") as mock_verify,
    ):
        mock_hash.side_effect = lambda x: f"hashed_{x}"
        mock_verify.side_effect = lambda p, h: h == f"hashed_{p}"
        yield


@pytest.fixture(autouse=True)
def disable_rate_limits():
    from app.limiter import limiter

    was_enabled = limiter.enabled
    limiter.enabled = False
    yield
    limiter.enabled = was_enabled


def test_auth_login_invalid():
    # Test login with invalid credentials
    # The app returns 403 Forbidden for invalid credentials in app/routers/auth.py
    response = client.post(
        "/api/v1/auth/login", data={"username": "wrong@example.com", "password": "wrongpassword"}
    )
    assert response.status_code == 403
    assert "detail" in response.json()


def test_auth_register_success(db_session):
    # Ensure MASTER_INVITE_CODE is set for tests
    from app.config import settings

    settings.MASTER_INVITE_CODE = "testcode"
    unique_id = str(uuid.uuid4())[:8]
    payload = {
        "email": f"new_{unique_id}@example.com",
        "password": "StrongP@ss1",
        "full_name": "New User",
        "organization_name": f"New Org {unique_id}",
        "invite_code": "testcode",
    }

    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == payload["email"]
    assert data["role"] == "admin"  # First user in org should be admin


def test_auth_register_duplicate_email(db_session):
    from app.config import settings

    settings.MASTER_INVITE_CODE = "testcode"
    unique_id = str(uuid.uuid4())[:8]
    email = f"dup_{unique_id}@example.com"
    payload = {
        "email": email,
        "password": "StrongP@ss1",
        "full_name": "User 1",
        "organization_name": f"Org {unique_id}",
        "invite_code": "testcode",
    }

    # First registration
    client.post("/api/v1/auth/register", json=payload)

    # Second registration with same email
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 400
    assert "Email already registered" in response.json()["detail"]


def test_existing_org_accepts_exact_existing_user_domain(db_session):
    from app import models
    from app.config import settings

    settings.MASTER_INVITE_CODE = "testcode"
    unique_id = str(uuid.uuid4())[:8]
    org_name = f"Acme {unique_id}"
    owner_email = f"owner_{unique_id}@acme.example"

    first = client.post(
        "/api/v1/auth/register",
        json={
            "email": owner_email,
            "password": "StrongP@ss1",
            "full_name": "Owner",
            "organization_name": org_name,
            "invite_code": "testcode",
        },
    )
    assert first.status_code == 201

    second = client.post(
        "/api/v1/auth/register",
        json={
            "email": f"member_{unique_id}@acme.example",
            "password": "StrongP@ss1",
            "full_name": "Member",
            "organization_name": org_name,
            "invite_code": "testcode",
        },
    )

    assert second.status_code == 201
    assert second.json()["role"] == "viewer"
    users = db_session.query(models.User).filter(models.User.email.like(f"%{unique_id}%")).all()
    assert len(users) == 2


def test_existing_org_rejects_lookalike_domain(db_session):
    from app.config import settings

    settings.MASTER_INVITE_CODE = "testcode"
    unique_id = str(uuid.uuid4())[:8]
    org_name = f"Acme Security {unique_id}"

    first = client.post(
        "/api/v1/auth/register",
        json={
            "email": f"owner_{unique_id}@acme.example",
            "password": "StrongP@ss1",
            "full_name": "Owner",
            "organization_name": org_name,
            "invite_code": "testcode",
        },
    )
    assert first.status_code == 201

    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": f"attacker_{unique_id}@evilacme.example",
            "password": "StrongP@ss1",
            "full_name": "Attacker",
            "organization_name": org_name,
            "invite_code": "testcode",
        },
    )

    assert response.status_code == 400
    assert "domain does not match" in response.json()["detail"]


def test_auth_login_success(db_session):
    unique_id = str(uuid.uuid4())[:8]
    email = f"user_{unique_id}@example.com"
    password = "StrongP@ss1"

    # Register first
    from app.config import settings

    settings.MASTER_INVITE_CODE = "testcode"
    client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "full_name": "User",
            "organization_name": f"Org {unique_id}",
            "invite_code": "testcode",
        },
    )

    # Now login
    response = client.post("/api/v1/auth/login", data={"username": email, "password": password})
    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.json()}"
    )
    data = response.json()
    # JWT is delivered exclusively via httpOnly cookie (security) — not in response body
    assert "access_token" not in data, "JWT must not appear in response body"
    assert data.get("message") == "Authentication successful"


def test_inactive_user_cannot_login(db_session):
    from app import auth, models

    unique_id = str(uuid.uuid4())[:8]
    org = models.Organization(name=f"Inactive Org {unique_id}")
    db_session.add(org)
    db_session.commit()
    user = models.User(
        email=f"inactive_{unique_id}@example.com",
        hashed_password=auth.get_password_hash("StrongP@ss1"),
        full_name="Inactive User",
        organization_id=org.id,
        role=models.RoleEnum.ADMIN,
        is_active=False,
    )
    db_session.add(user)
    db_session.commit()

    response = client.post(
        "/api/v1/auth/login",
        data={"username": user.email, "password": "StrongP@ss1"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Account is inactive"


def test_inactive_user_existing_token_is_rejected(db_session):
    from app import auth, models

    unique_id = str(uuid.uuid4())[:8]
    org = models.Organization(name=f"Inactive Token Org {unique_id}")
    db_session.add(org)
    db_session.commit()
    user = models.User(
        email=f"inactive_token_{unique_id}@example.com",
        hashed_password=auth.get_password_hash("StrongP@ss1"),
        full_name="Inactive Token User",
        organization_id=org.id,
        role=models.RoleEnum.ADMIN,
        is_active=False,
    )
    db_session.add(user)
    db_session.commit()
    token = auth.create_access_token({"sub": user.email})

    response = client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Account is inactive"


def test_organizations_me_unauthorized():
    client.cookies.clear()
    response = client.get("/api/v1/organizations/me")
    assert response.status_code == 401
