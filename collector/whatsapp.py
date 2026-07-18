"""WhatsApp Web collection scaffold.

This module owns collection only. It intentionally does not contain database,
AI, or presentation logic.
"""

from __future__ import annotations


def fetch_messages() -> list[dict[str, str]]:
    """Return newly collected messages from WhatsApp Web.

    The Playwright implementation will be added in the collector milestone.
    """
    return []


def sync() -> int:
    """Synchronize messages from WhatsApp Web and return the number collected."""
    return len(fetch_messages())
