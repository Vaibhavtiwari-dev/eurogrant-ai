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
