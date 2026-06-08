import os

import pytest

os.environ["ENVIRONMENT"] = "development"

# Must set DATABASE_URL before any app import so that the worker's SessionLocal
# (from app.database) connects to the same SQLite file as the test session.
TEST_DB_FILE = "test_worker.db"
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_FILE}"

import uuid
from unittest.mock import AsyncMock, MagicMock

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import models
from app.auth import get_current_user
from app.database import Base, get_db
from app.main import app

SQLALCHEMY_DATABASE_URL = f"sqlite:///{TEST_DB_FILE}"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session", autouse=True)
def create_test_db():
    # Import all models to ensure they are registered with Base.metadata
    if os.path.exists(TEST_DB_FILE):
        os.remove(TEST_DB_FILE)
    Base.metadata.create_all(bind=engine)
    # Also create tables on the app's database engine — Celery worker tasks
    # use SessionLocal() directly (bypassing conftest's override of get_db)
    # and in CI this hits a separate SQLite file.
    from app.database import engine as app_engine

    if "sqlite" in str(app_engine.url):
        Base.metadata.create_all(bind=app_engine)
    yield
    # On Windows, we might have file locks, so we don't remove here.
    # It will be removed at the start of the next run if it exists.


@pytest.fixture
def db_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


def override_get_db():
    db = None
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        if db is not None:
            db.close()


@pytest.fixture(autouse=True)
def _setup_db_override():
    """Set and tear down the database dependency override for every test."""
    app.dependency_overrides[get_db] = override_get_db
    yield
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def mock_s3():
    # Use AsyncMock for async function
    mock = AsyncMock()
    from app.services.s3 import s3_service

    old_upload = s3_service.upload_fileobj
    s3_service.upload_fileobj = mock
    yield mock
    s3_service.upload_fileobj = old_upload


@pytest.fixture
def mock_worker():
    mock = MagicMock()
    from app.worker import process_company_document

    old_delay = process_company_document.delay
    process_company_document.delay = mock
    yield mock
    process_company_document.delay = old_delay


@pytest.fixture
def test_user(db_session):
    unique_id = str(uuid.uuid4())[:8]
    org = models.Organization(name=f"Test Org {unique_id}", subscription_tier="growth")
    db_session.add(org)
    db_session.commit()

    user = models.User(
        email=f"test_{unique_id}@example.com",
        full_name="Test User",
        hashed_password="hashed_password",
        role=models.RoleEnum.ADMIN,
        organization_id=org.id,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    db_session.refresh(org)
    return user


@pytest.fixture
def authenticated_client(test_user):
    def override_get_current_user():
        return test_user

    app.dependency_overrides[get_current_user] = override_get_current_user
    from fastapi.testclient import TestClient

    client = TestClient(app)
    yield client
    del app.dependency_overrides[get_current_user]
