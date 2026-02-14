"""Neon PostgreSQL connection and table creation."""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from src.data.models import Base
from src.utils.config import DATABASE_URL


def get_engine():
    """Create SQLAlchemy engine for Neon with connection pooling and SSL."""
    return create_engine(
        DATABASE_URL,
        connect_args={"sslmode": "require"},
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
    )


engine = get_engine() if DATABASE_URL else None
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine) if engine else None


def create_tables(eng=None):
    """Create all tables. Uses global engine if eng not provided."""
    if eng is None:
        eng = engine
    if eng is None:
        return
    from src.data import models  # noqa: F401 - register models
    Base.metadata.create_all(bind=eng)


def get_session() -> Session:
    """Return a new session (caller should close or use as context)."""
    if SessionLocal is None:
        raise RuntimeError("Database not configured: DATABASE_URL missing")
    return SessionLocal()
