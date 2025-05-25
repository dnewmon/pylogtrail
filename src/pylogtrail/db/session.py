from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from typing import Generator
from functools import cache
import os
import argparse


@cache
def parse_database_cli_params():
    """Parse command line arguments for database configuration"""
    parser = argparse.ArgumentParser(description="PyLogTrail Database Configuration")
    parser.add_argument(
        "--database-url",
        help="SQLAlchemy database URL (overrides PYLOGTRAIL_DATABASE_URL environment variable)",
        default=None,
    )

    known, unknown = parser.parse_known_args()
    return known


@cache
def get_database_url() -> str:
    """Get database URL from command line, environment variable, or use default SQLite database.

    Priority order:
    1. Command line --database-url argument
    2. PYLOGTRAIL_DATABASE_URL environment variable
    3. Default SQLite database

    Returns:
        str: A valid SQLAlchemy database URL
    """
    args = parse_database_cli_params()
    if args.database_url is not None:
        return args.database_url

    default_url = "sqlite:///pylogtrail.db"
    return os.getenv("PYLOGTRAIL_DATABASE_URL", default_url)


def create_db_engine():
    """Create SQLAlchemy engine with appropriate settings"""
    return create_engine(
        get_database_url(),
        pool_size=5,
        max_overflow=10,
        pool_timeout=30,
        pool_recycle=1800,  # Recycle connections after 30 minutes
        echo=False,  # Set to True for SQL query logging
    )


# Create session factory
SessionLocal = sessionmaker(bind=create_db_engine())


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """Context manager for database sessions"""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db():
    """Initialize database by creating all tables"""
    from .models import Base

    Base.metadata.create_all(bind=create_db_engine())
