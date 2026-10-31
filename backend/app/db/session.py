"""
Database session management using SQLAlchemy 2.x and direct PostgreSQL.
"""

import logging
from functools import lru_cache
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config.settings import get_settings

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_engine():
    """
    Create and cache a SQLAlchemy engine configured for serverless PostgreSQL access.
    Uses Supabase Session Pooler (port 5432).
    """
    settings = get_settings()
    import os
    db_url = (
        settings.SUPABASE_DATABASE_URL
        or settings.DATABASE_URL
        or os.getenv("POSTGRES_URL", "")
        or os.getenv("POSTGRES_PRISMA_URL", "")
    )
    if not db_url or not db_url.strip():
        logger.error(
            "CRITICAL: Neither SUPABASE_DATABASE_URL, DATABASE_URL, nor POSTGRES_URL is configured. "
            "Database connections will fail unless valid connection credentials are provided."
        )
        db_url = "postgresql://postgres:postgres@localhost:5432/postgres"

    # Normalize url scheme if necessary
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)

    connect_args = {
        "keepalives": 1,
        "keepalives_idle": 30,
        "keepalives_interval": 10,
        "keepalives_count": 5,
    }

    # Detect Vercel serverless environment (Vercel automatically sets VERCEL=1)
    is_vercel = bool(os.getenv("VERCEL"))

    # In Vercel serverless microVMs, each instance handles 1 concurrent request.
    # pool_size=2 and max_overflow=1 allows up to 3 total connections per warm instance,
    # ensuring warm connection reuse without multiplying connection exhaustion on Supabase
    # across multiple concurrent serverless function instances (budget: 60 max, 42 headroom).
    #
    # In persistent environments (local Docker / standalone container), pool_size=10 and
    # max_overflow=5 (up to 15 connections) supports high-concurrency burst traffic cleanly.
    default_pool_size = 2 if is_vercel else 10
    default_max_overflow = 1 if is_vercel else 5

    pool_size = int(os.getenv("DB_POOL_SIZE", str(default_pool_size)))
    max_overflow = int(os.getenv("DB_MAX_OVERFLOW", str(default_max_overflow)))

    return create_engine(
        db_url,
        pool_size=pool_size,
        max_overflow=max_overflow,
        pool_pre_ping=True,
        pool_recycle=300,
        pool_timeout=15,
        connect_args=connect_args,
    )


@lru_cache(maxsize=1)
def get_sessionmaker():
    """Create and cache the sessionmaker bound to the engine."""
    return sessionmaker(autocommit=False, autoflush=False, bind=get_engine())


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that yields a SQLAlchemy Session.
    Ensures connection is closed cleanly after each request.
    """
    SessionLocal = get_sessionmaker()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
