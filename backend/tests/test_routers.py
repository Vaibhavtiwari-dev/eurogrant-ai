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
    from datetime import UTC, datetime, timedelta

    from app import models

    unique_id = str(uuid.uuid4())[:8]
    email = f"new_{unique_id}@example.com"

    org = models.Organization(name=f"New Org {unique_id}")
    db_session.add(org)
    db_session.commit()
    sys_user = models.User(
        email=f"sys_{unique_id}_{uuid.uuid4().hex[:4]}@sys.com",
        hashed_password="sys",
        full_name="sys",
        organization_id=org.id,
        role="admin",
        is_active=True,
    )
    db_session.add(sys_user)
    db_session.commit()

    invitation = models.UserInvitation(
        invited_by_id=sys_user.id,
        email=email,
        organization_id=org.id,
        invite_code=f"testcode_{unique_id}",
        expires_at=datetime.now(UTC) + timedelta(days=7),
    )
    db_session.add(invitation)
    db_session.commit()

    payload = {
        "email": email,
        "password": "StrongP@ss1",
        "full_name": "New User",
        "invite_code": f"testcode_{unique_id}",
    }

    response = client.post("/api/v1/auth/register", json=payload)
    print(response.json())
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == payload["email"]
    assert data["role"] == "viewer"


def test_auth_register_duplicate_email(db_session):
    from datetime import UTC, datetime, timedelta

    from app import models

    unique_id = str(uuid.uuid4())[:8]
    email = f"dup_{unique_id}@example.com"

    org = models.Organization(name=f"Dup Org {unique_id}")
    db_session.add(org)
    db_session.commit()
    sys_user = models.User(
        email=email,
        hashed_password="sys",
        full_name="sys",
        organization_id=org.id,
        role="admin",
        is_active=True,
    )
    db_session.add(sys_user)
    db_session.commit()

    invitation = models.UserInvitation(
        invited_by_id=sys_user.id,
        email=email,
        organization_id=org.id,
        invite_code=f"testcode_{unique_id}",
        expires_at=datetime.now(UTC) + timedelta(days=7),
    )
    db_session.add(invitation)
    db_session.commit()

    payload = {
        "email": email,
        "password": "StrongP@ss1",
        "full_name": "User 1",
        "invite_code": f"testcode_{unique_id}",
    }

    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 400
    assert "Email already registered" in response.json()["detail"]


def test_auth_login_success(db_session):
    from datetime import UTC, datetime, timedelta

    from app import models

    unique_id = str(uuid.uuid4())[:8]
    email = f"user_{unique_id}@example.com"
    password = "StrongP@ss1"

    org = models.Organization(name=f"Login Org {unique_id}")
    db_session.add(org)
    db_session.commit()
    sys_user = models.User(
        email=f"sys_{unique_id}_{uuid.uuid4().hex[:4]}@sys.com",
        hashed_password="sys",
        full_name="sys",
        organization_id=org.id,
        role="admin",
        is_active=True,
    )
    db_session.add(sys_user)
    db_session.commit()

    invitation = models.UserInvitation(
        invited_by_id=sys_user.id,
        email=email,
        organization_id=org.id,
        invite_code=f"testcode_{unique_id}",
        expires_at=datetime.now(UTC) + timedelta(days=7),
    )
    db_session.add(invitation)
    db_session.commit()

    client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "full_name": "User",
            "invite_code": f"testcode_{unique_id}",
        },
    )

    # Now login
    response = client.post("/api/v1/auth/login", data={"username": email, "password": password})
    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.json()}"
    )
    data = response.json()
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
