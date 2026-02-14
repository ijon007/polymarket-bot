"""Neon PostgreSQL connection and table creation."""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.utils.config import DATABASE_URL
from src.data.models import Base

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=5,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_session():
    """Return a new database session."""
    return SessionLocal()


def create_all_tables():
    """Create all tables defined in models."""
    Base.metadata.create_all(bind=engine)
