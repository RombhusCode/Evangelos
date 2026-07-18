"""Database engine and session helpers."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from database.models import Base

DATABASE_PATH = Path("data") / "evangelos.sqlite3"
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

engine = create_engine(DATABASE_URL, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def initialize_database() -> None:
    """Create the SQLite database and tables if they do not already exist."""
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)


def get_session() -> Iterator[Session]:
    """Yield a database session and close it after use."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
