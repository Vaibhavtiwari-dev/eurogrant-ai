import pytest
from app.auth import create_access_token, get_password_hash, verify_password
from datetime import timedelta

def test_create_access_token():
    data = {"sub": "test@example.com"}
    token = create_access_token(data)
    assert token is not None
    assert isinstance(token, str)

def test_token_expiration():
    data = {"sub": "test@example.com"}
    expires = timedelta(minutes=-1) # Already expired
    token = create_access_token(data, expires_delta=expires)
    assert token is not None

def test_password_hashing():
    password = "SuperSecretPassword123!"
    hashed = get_password_hash(password)
    assert hashed != password
    assert len(hashed) > 0

    # Verify correct password matches
    assert verify_password(password, hashed) is True

    # Verify incorrect password fails
    assert verify_password("WrongPassword123", hashed) is False


class TestPasswordComplexity:
    """Tests for password complexity validation in schemas.UserCreate."""

    def _make_user(self, password: str):
        """Helper to create a UserCreate instance with a given password."""
        from app.schemas import UserCreate
        return UserCreate(
            email="test@example.com",
            password=password,
            full_name="Test User",
            organization_name="Test Org",
            invite_code="TEST_CODE"
        )

    def test_valid_complex_password(self):
        user = self._make_user("StrongP@ss1")
        assert user.password == "StrongP@ss1"

    def test_missing_uppercase(self):
        with pytest.raises(ValueError, match="uppercase"):
            self._make_user("weakpass1!")

    def test_missing_lowercase(self):
        with pytest.raises(ValueError, match="lowercase"):
            self._make_user("WEAKPASS1!")

    def test_missing_digit(self):
        with pytest.raises(ValueError, match="digit"):
            self._make_user("WeakPass!")

    def test_missing_special(self):
        with pytest.raises(ValueError, match="special"):
            self._make_user("WeakPass1")

    def test_too_short(self):
        with pytest.raises(ValueError, match="at least 8"):
            self._make_user("Sh0rt!A")


class TestLoginNoJwtInBody:
    """Tests that login endpoint does not return JWT in response body."""

    def test_login_response_no_token(self, db_session):
        """Verify the login success response does not contain access_token field."""
        from fastapi.testclient import TestClient
        from app.main import app
        from app import models
        from app.auth import get_password_hash

        # Create a real org and user so login succeeds
        org = models.Organization(name="Login Test Org", subscription_tier="growth")
        db_session.add(org)
        db_session.commit()

        user = models.User(
            email="logintest@example.com",
            hashed_password=get_password_hash("TestPass123!"),
            full_name="Login Test User",
            role=models.RoleEnum.ADMIN,
            organization_id=org.id,
        )
        db_session.add(user)
        db_session.commit()

        client = TestClient(app)
        response = client.post(
            "/api/v1/auth/login",
            data={"username": "logintest@example.com", "password": "TestPass123!"},
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.json()}"
        body = response.json()
        assert "access_token" not in body, "JWT must not appear in response body"
        assert body.get("message") == "Authentication successful"
