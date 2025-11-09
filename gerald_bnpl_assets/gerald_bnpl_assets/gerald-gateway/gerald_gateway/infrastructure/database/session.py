"""Database session management with connection pooling"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from gerald_gateway.config import settings

# Connection pool: max 20 connections, recycle after 1 hour to avoid stale connections
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,  # Verify connections before using
    pool_size=10,
    max_overflow=10,
    pool_recycle=3600,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Session:
    """Dependency injection for database sessions"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
