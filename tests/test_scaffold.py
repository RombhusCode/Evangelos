"""Scaffold verification tests."""

from __future__ import annotations

from ai import summarize_messages
from collector import fetch_messages, sync
from database.session import initialize_database


def test_database_initializes() -> None:
    """The database layer can create its SQLite schema."""
    initialize_database()


def test_collector_scaffold_is_empty() -> None:
    """The collector scaffold starts with no collected messages."""
    assert fetch_messages() == []
    assert sync() == 0


def test_ai_scaffold_handles_empty_messages() -> None:
    """The AI scaffold has a graceful empty state."""
    assert summarize_messages([]) == "No messages to summarize."
