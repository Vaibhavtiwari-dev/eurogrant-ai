
from contextlib import contextmanager

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import settings

load_dotenv()

SQLALCHEMY_DATABASE_URL = settings.DATABASE_URL
if not SQLALCHEMY_DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL environment variable is required. "
        "No default fallback is provided — explicitly set DATABASE_URL in production."
    )

connect_args: dict = {}
if "sqlite" in SQLALCHEMY_DATABASE_URL:
    # SQLite requires check_same_thread=False and a busy timeout when accessed
    # from multiple threads (e.g. FastAPI's lifespan events + Celery workers).
    # PostgreSQL ignores these options entirely.
    connect_args = {"check_same_thread": False, "timeout": 30}

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def session_scope():
    """Provide a transactional scope around a series of operations."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
