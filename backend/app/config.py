
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    ENVIRONMENT: str = "production"
    DATABASE_URL: str

    JWT_SECRET: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    MASTER_INVITE_CODE: str | None = None

    CELERY_BROKER_URL: str = "redis://redis:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/0"
    CELERY_ALWAYS_EAGER: str = "false"

    OPENAI_API_KEY: str | None = None
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"

    STORAGE_BACKEND: str = "s3"
    AWS_ACCESS_KEY_ID: str | None = None
    AWS_SECRET_ACCESS_KEY: str | None = None
    AWS_REGION: str = "eu-central-1"
    AWS_SES_REGION: str = "eu-central-1"
    SES_SENDER_EMAIL: str = "alerts@eurogrant.ai"
    S3_BUCKET_NAME: str | None = None

    APP_BASE_URL: str = "https://eurogrant.ai"

    PINECONE_API_KEY: str | None = None
    PINECONE_INDEX_NAME: str = "eurogrant"
    EMBEDDING_DIMENSION: int = 1536
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    PINECONE_ENVIRONMENT: str = "us-east-1"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()  # type: ignore
