"""Persistence model tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from database.models import Base, Chat, ChatTrackingStatus, Message, Source, SyncState


def utc_now() -> datetime:
    """Return the current UTC timestamp."""
    return datetime.now(UTC)


@pytest.fixture()
def session() -> Session:
    """Create an isolated SQLite database for model tests."""
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)

    with Session(engine) as session:
        yield session


def test_models_can_be_created(session: Session) -> None:
    """The persistence models can be inserted together."""
    source = Source(name="whatsapp", display_name="WhatsApp")
    chat = Chat(
        source=source,
        external_id="family-chat",
        display_name="Family",
        initial_import_after=utc_now() - timedelta(days=15),
    )
    message = Message(
        chat=chat,
        source=source,
        source_message_id="wa-message-1",
        sender="Kapil",
        body="Dinner at 8?",
        sent_at=utc_now(),
    )
    sync_state = SyncState(chat=chat, last_message_sent_at=message.sent_at)

    session.add_all([source, chat, message, sync_state])
    session.commit()

    assert source.id is not None
    assert chat.id is not None
    assert message.id is not None
    assert sync_state.id is not None
    assert chat.tracking_status == ChatTrackingStatus.ACTIVE.value


def test_relationships_connect_source_chat_messages_and_sync_state(
    session: Session,
) -> None:
    """Relationships expose the normalized persistence graph."""
    source = Source(name="whatsapp", display_name="WhatsApp")
    chat = Chat(source=source, external_id="school", display_name="School")
    message = Message(
        chat=chat,
        source=source,
        source_message_id="wa-message-2",
        sender="Teacher",
        body="Class starts at 9.",
        sent_at=utc_now(),
    )
    sync_state = SyncState(chat=chat, source_cursor="cursor-1")

    session.add_all([source, chat, message, sync_state])
    session.commit()
    session.refresh(source)

    assert source.chats == [chat]
    assert source.messages == [message]
    assert chat.source == source
    assert chat.messages == [message]
    assert chat.sync_state == sync_state
    assert message.chat == chat
    assert message.source == source


def test_duplicate_source_message_ids_are_rejected(session: Session) -> None:
    """A source cannot store the same message id more than once."""
    source = Source(name="whatsapp", display_name="WhatsApp")
    chat = Chat(source=source, external_id="work", display_name="Work")
    sent_at = utc_now()

    session.add_all(
        [
            Message(
                chat=chat,
                source=source,
                source_message_id="wa-duplicate",
                sender="Asha",
                body="First copy",
                sent_at=sent_at,
            ),
            Message(
                chat=chat,
                source=source,
                source_message_id="wa-duplicate",
                sender="Asha",
                body="Second copy",
                sent_at=sent_at,
            ),
        ]
    )

    with pytest.raises(IntegrityError):
        session.commit()


def test_duplicate_tracked_chats_are_rejected(session: Session) -> None:
    """A source cannot track the same external chat twice."""
    source = Source(name="whatsapp", display_name="WhatsApp")
    session.add_all(
        [
            source,
            Chat(source=source, external_id="same-chat", display_name="Same Chat"),
            Chat(source=source, external_id="same-chat", display_name="Same Chat"),
        ]
    )

    with pytest.raises(IntegrityError):
        session.commit()
