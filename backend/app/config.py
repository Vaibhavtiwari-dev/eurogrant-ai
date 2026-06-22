import ipaddress
from enum import StrEnum
from typing import Self
from urllib.parse import urlparse

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class EnvironmentEnum(StrEnum):
    """Allowed environment values for strict validation."""

    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


class Settings(BaseSettings):
    ENVIRONMENT: EnvironmentEnum = EnvironmentEnum.PRODUCTION
    DATABASE_URL: str

    JWT_SECRET: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    CELERY_BROKER_URL: str = "redis://redis:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/0"
    CELERY_ALWAYS_EAGER: str = "false"

    OPENAI_API_KEY: str | None = None
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    PROPOSAL_LLM_MODEL: str = "gpt-4o-mini"
    PROPOSAL_SECTION_MODEL: str = "gpt-4o-mini"
    PROPOSAL_MAX_SECTIONS: int = Field(default=7, ge=1, le=10)
    PROPOSAL_LLM_TIMEOUT_SECONDS: int = Field(default=60, ge=5, le=180)
    PROPOSAL_SECTION_MAX_TOKENS: int = Field(default=1800, ge=256, le=4096)
    PROPOSAL_CONTEXT_MAX_CHARS: int = Field(default=20000, ge=1000, le=100000)
    PROPOSAL_SECTION_MAX_JSON_BYTES: int = Field(default=200000, ge=1000, le=1000000)

    STORAGE_BACKEND: str = "s3"
    AWS_ACCESS_KEY_ID: str | None = None
    AWS_SECRET_ACCESS_KEY: str | None = None
    AWS_REGION: str = "eu-central-1"
    AWS_SES_REGION: str = "eu-central-1"
    SES_SENDER_EMAIL: str = "alerts@eurogrant.ai"
    S3_BUCKET_NAME: str | None = None

    APP_BASE_URL: str = "https://eurogrant.ai"

    SENTRY_DSN: str | None = None

    STRIPE_SECRET_KEY: str | None = None
    STRIPE_WEBHOOK_SECRET: str | None = None
    STRIPE_GROWTH_PRICE_ID: str | None = None
    STRIPE_SCALE_PRICE_ID: str | None = None
    STRIPE_AGENCY_PRICE_ID: str | None = None

    POSTGRES_USER: str | None = None
    POSTGRES_PASSWORD: str | None = None
    POSTGRES_DB: str | None = None

    # Test DB
    TEST_DATABASE_URL: str = "sqlite:///./test.db"

    PINECONE_API_KEY: str | None = None
    PINECONE_INDEX_NAME: str = "eurogrant"
    EMBEDDING_DIMENSION: int = 1536
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    PINECONE_ENVIRONMENT: str = "us-east-1"
    TRUSTED_PROXY_CIDRS: str = "127.0.0.1/32,::1/128"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    def __repr__(self) -> str:
        """Mask sensitive fields in string representation to prevent API key exposure in logs."""
        safe_fields = {}
        sensitive_keywords = ["API_KEY", "SECRET", "PASSWORD", "TOKEN"]
        for key, value in self.__dict__.items():
            if any(s in key.upper() for s in sensitive_keywords):
                safe_fields[key] = "***MASKED***" if value else None
            else:
                safe_fields[key] = value
        return f"Settings({safe_fields})"

    @model_validator(mode="after")
    def validate_production_redis(self) -> Self:
        if self.ENVIRONMENT != EnvironmentEnum.PRODUCTION:
            return self

        for redis_url in (self.CELERY_BROKER_URL, self.CELERY_RESULT_BACKEND):
            parsed = urlparse(redis_url)
            if not parsed.password:
                raise ValueError("Production Redis URLs must include authentication")
            if parsed.scheme not in {"redis", "rediss"}:
                raise ValueError("Redis URLs must use redis:// or rediss://")
            if parsed.scheme == "redis" and not _is_private_redis_host(parsed.hostname):
                raise ValueError(
                    "Production Redis connections to non-private hosts must use rediss://"
                )
        return self

    @model_validator(mode="after")
    def validate_production_secrets(self) -> Self:
        if self.ENVIRONMENT not in (EnvironmentEnum.PRODUCTION, EnvironmentEnum.STAGING):
            return self

        required_keys = [
            "OPENAI_API_KEY",
            "PINECONE_API_KEY",
            "STRIPE_SECRET_KEY",
            "STRIPE_WEBHOOK_SECRET",
            "AWS_ACCESS_KEY_ID",
            "AWS_SECRET_ACCESS_KEY",
            "S3_BUCKET_NAME",
        ]
        for key in required_keys:
            if not getattr(self, key):
                raise ValueError(f"{key} must be set in production/staging environments")
        return self


def _is_private_redis_host(hostname: str | None) -> bool:
    if not hostname:
        return False
    if hostname in {"redis", "localhost"}:
        return True
    try:
        return ipaddress.ip_address(hostname).is_private
    except ValueError:
        return hostname.endswith(".internal") or hostname.endswith(".local")


def mask_sensitive(value: str | None, show_last: int = 4) -> str:
    """Mask sensitive string for safe logging.

    Args:
        value: The sensitive string to mask.
        show_last: Number of characters to show at the end.

    Returns:
        Masked string like '****abcd' or 'None' if value is None.
    """
    if not value:
        return "None"
    if len(value) <= show_last:
        return "***"
    return "*" * (len(value) - show_last) + value[-show_last:]


settings = Settings()  # type: ignore
