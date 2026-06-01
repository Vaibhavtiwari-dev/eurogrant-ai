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

    def test_login_response_no_token(self, authenticated_client):
        """Verify the login success response does not contain access_token field."""
        from fastapi.testclient import TestClient
        from app.main import app
        client = TestClient(app)
        # Login requires form-encoded data via OAuth2PasswordRequestForm
        response = client.post(
            "/api/v1/auth/login",
            data={"username": "test@example.com", "password": "testpass"},
        )
        # The test bypasses real auth via dependency override,
        # so we check the response shape is correct
        body = response.json()
        assert "access_token" not in body, "JWT must not appear in response body"
        assert body.get("message") == "Authentication successful"
