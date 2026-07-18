"""CRUD helpers for Evangelos persistence."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from database.models import Message


def list_messages(session: Session, limit: int = 50) -> list[Message]:
    """Return recent messages from the database."""
    statement = select(Message).order_by(Message.sent_at.desc()).limit(limit)
    return list(session.scalars(statement))
