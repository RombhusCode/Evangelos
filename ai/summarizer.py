"""AI summarization scaffold.

AI reads structured data from the database layer and never from collectors.
"""

from __future__ import annotations


def summarize_messages(messages: list[str]) -> str:
    """Return a summary for message text.

    The Ollama-backed implementation belongs in the AI milestone.
    """
    if not messages:
        return "No messages to summarize."
    return "Summarization is not implemented yet."
