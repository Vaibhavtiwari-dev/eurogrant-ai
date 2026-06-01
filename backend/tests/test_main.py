from fastapi.testclient import TestClient
from app.main import app
import pytest

client = TestClient(app)

def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to EuroGrant AI API"}

def test_api_v1_exists():
    # Test an endpoint that exists but requires auth to verify routing
    response = client.get("/api/v1/users/me")
    assert response.status_code == 401 # Unauthorized because no token provided


class TestSecurityHeaders:
    """All responses must carry security headers."""

    def test_csp_header_present(self):
        response = client.get("/")
        assert "Content-Security-Policy" in response.headers
        assert "default-src 'self'" in response.headers["Content-Security-Policy"]

    def test_hsts_header_present(self):
        response = client.get("/")
        assert "Strict-Transport-Security" in response.headers
        assert "max-age=31536000" in response.headers["Strict-Transport-Security"]

    def test_xframe_options(self):
        response = client.get("/")
        assert response.headers.get("X-Frame-Options") == "DENY"

    def test_xcontent_type_options(self):
        response = client.get("/")
        assert response.headers.get("X-Content-Type-Options") == "nosniff"

    def test_permissions_policy(self):
        response = client.get("/")
        assert "Permissions-Policy" in response.headers
        assert "geolocation=()" in response.headers["Permissions-Policy"]

    def test_referrer_policy(self):
        response = client.get("/")
        assert response.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"


class TestCsrfProtection:
    """CSRF middleware must block invalid origins."""

    def test_csrf_blocks_unauthorized_origin(self):
        response = client.post(
            "/api/v1/auth/login",
            data={"username": "test@example.com", "password": "pass"},
            headers={"Origin": "https://evil.com"},
        )
        assert response.status_code == 403
        assert "CSRF" in response.json().get("detail", "")

    def test_csrf_allows_same_origin(self):
        response = client.post(
            "/api/v1/auth/login",
            data={"username": "test@example.com", "password": "pass"},
            headers={"Origin": "http://localhost:3000"},
        )
        # Should not be blocked by CSRF (may 403 for auth failure, not CSRF)
        assert response.status_code != 403 or "CSRF" not in response.json().get("detail", "")


class TestHealthEndpoint:
    """The /health endpoint must exist and return correct structure."""

    def test_health_returns_200(self):
        response = client.get("/health")
        # May return 503 if no DB/Redis, but must be valid JSON
        assert response.status_code in (200, 503)
        body = response.json()
        assert "status" in body
        assert body["status"] in ("healthy", "degraded")

    def test_health_has_db_and_redis_keys(self):
        response = client.get("/health")
        body = response.json()
        assert "database" in body
        assert "redis" in body
