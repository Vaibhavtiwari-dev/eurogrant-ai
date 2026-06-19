from contextlib import asynccontextmanager, contextmanager

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import settings

load_dotenv()

SQLALCHEMY_DATABASE_URL = settings.DATABASE_URL
if not SQLALCHEMY_DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL environment variable is required. "
        "No default fallback is provided — explicitly set DATABASE_URL in production."
    )

# --- Sync engine (for Celery workers and migrations) ---
connect_args: dict = {}
if "sqlite" in SQLALCHEMY_DATABASE_URL:
    connect_args = {"check_same_thread": False, "timeout": 30}

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# --- Async engine (for FastAPI routes) ---
async_connect_args: dict = {}
if "sqlite" in SQLALCHEMY_DATABASE_URL:
    # aiosqlite requires check_same_thread=False
    async_connect_args = {"check_same_thread": False}

# Convert sqlite:/// to sqlite+aiosqlite:/// for async driver
ASYNC_DATABASE_URL = SQLALCHEMY_DATABASE_URL
if SQLALCHEMY_DATABASE_URL.startswith("sqlite:///"):
    ASYNC_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("sqlite:///", "sqlite+aiosqlite:///", 1)
elif SQLALCHEMY_DATABASE_URL.startswith("sqlite://"):
    ASYNC_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("sqlite://", "sqlite+aiosqlite://", 1)

async_engine = create_async_engine(
    ASYNC_DATABASE_URL,
    connect_args=async_connect_args,
    pool_pre_ping=True,
)
AsyncSessionLocal = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


# --- Sync dependency (for Celery workers) ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# --- Async dependency (for FastAPI routes) ---
async def get_async_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@contextmanager
def session_scope():
    """Provide a transactional scope around a series of operations (sync)."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@asynccontextmanager
async def async_session_scope():
    """Provide a transactional scope around a series of operations (async)."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
