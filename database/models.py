"""SQLAlchemy models for Evangelos."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all database models."""


def utc_now() -> datetime:
    """Return the current UTC timestamp."""
    return datetime.now(UTC)


class ChatTrackingStatus(StrEnum):
    """Tracking states for chats explicitly selected by the user."""

    ACTIVE = "active"
    PAUSED = "paused"
    DELETED = "deleted"


class Source(Base):
    """A communication source such as WhatsApp, Gmail, or Slack."""

    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    chats: Mapped[list[Chat]] = relationship(
        back_populates="source",
        cascade="all, delete-orphan",
    )
    messages: Mapped[list[Message]] = relationship(back_populates="source")


class Chat(Base):
    """A user-selected conversation being tracked by Evangelos."""

    __tablename__ = "chats"
    __table_args__ = (
        UniqueConstraint("source_id", "external_id", name="uq_chats_source_external_id"),
        Index("ix_chats_source_status", "source_id", "tracking_status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id"), index=True)
    external_id: Mapped[str] = mapped_column(String(255))
    display_name: Mapped[str] = mapped_column(String(255), index=True)
    tracking_status: Mapped[str] = mapped_column(
        String(20),
        default=ChatTrackingStatus.ACTIVE.value,
        index=True,
    )
    initial_import_after: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utc_now,
        onupdate=utc_now,
    )

    source: Mapped[Source] = relationship(back_populates="chats")
    messages: Mapped[list[Message]] = relationship(
        back_populates="chat",
        cascade="all, delete-orphan",
    )
    sync_state: Mapped[SyncState | None] = relationship(
        back_populates="chat",
        cascade="all, delete-orphan",
        uselist=False,
    )


class Message(Base):
    """A message collected from an external communication source."""

    __tablename__ = "messages"
    __table_args__ = (
        UniqueConstraint(
            "source_id",
            "source_message_id",
            name="uq_messages_source_message_id",
        ),
        Index("ix_messages_chat_sent_at", "chat_id", "sent_at"),
        Index("ix_messages_source_sent_at", "source_id", "sent_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    chat_id: Mapped[int] = mapped_column(ForeignKey("chats.id"), index=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id"), index=True)
    source_message_id: Mapped[str] = mapped_column(String(255))
    sender: Mapped[str] = mapped_column(String(255), index=True)
    body: Mapped[str] = mapped_column(Text)
    sent_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    source_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    chat: Mapped[Chat] = relationship(back_populates="messages")
    source: Mapped[Source] = relationship(back_populates="messages")


class SyncState(Base):
    """Incremental synchronization state for a tracked chat."""

    __tablename__ = "sync_states"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    chat_id: Mapped[int] = mapped_column(
        ForeignKey("chats.id"),
        unique=True,
        index=True,
    )
    source_cursor: Mapped[str | None] = mapped_column(String(500), nullable=True)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_message_sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utc_now,
        onupdate=utc_now,
    )

    chat: Mapped[Chat] = relationship(back_populates="sync_state")
