"""Application configuration helpers."""

from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv


def load_settings() -> None:
    """Load local environment settings from a .env file when present."""
    load_dotenv()


def project_root() -> Path:
    """Return the repository root path."""
    return Path(__file__).resolve().parents[1]
