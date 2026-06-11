import pytest
from pydantic import ValidationError

from app.config import Settings


def _production_settings(**overrides):
    values = {
        "ENVIRONMENT": "production",
        "DATABASE_URL": "postgresql://user:password@db/eurogrant",
        "JWT_SECRET": "test-secret",
        "CELERY_BROKER_URL": "redis://:redis-password@redis:6379/0",
        "CELERY_RESULT_BACKEND": "redis://:redis-password@redis:6379/0",
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def test_production_rejects_unauthenticated_redis():
    with pytest.raises(ValidationError, match="Redis URLs must include authentication"):
        _production_settings(
            CELERY_BROKER_URL="redis://redis:6379/0",
            CELERY_RESULT_BACKEND="redis://redis:6379/0",
        )


def test_production_accepts_authenticated_private_redis():
    settings = _production_settings()

    assert settings.CELERY_BROKER_URL.startswith("redis://:")


def test_production_requires_tls_for_non_private_redis():
    with pytest.raises(ValidationError, match="rediss"):
        _production_settings(
            CELERY_BROKER_URL="redis://:password@redis.example.com:6379/0",
            CELERY_RESULT_BACKEND="redis://:password@redis.example.com:6379/0",
        )
