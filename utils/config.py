"""Application configuration helpers."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


def load_settings() -> None:
    """Load local environment settings from a .env file when present."""
    load_dotenv()


def project_root() -> Path:
    """Return the repository root path."""
    return Path(__file__).resolve().parents[1]


def data_dir() -> Path:
    """Return the directory used for local application data."""
    configured_path = os.getenv("EVANGELOS_DATA_DIR")
    if configured_path:
        return Path(configured_path).expanduser()
    return project_root() / "data"


def whatsapp_profile_dir() -> Path:
    """Return the persistent browser profile directory for WhatsApp Web."""
    configured_path = os.getenv("EVANGELOS_WHATSAPP_PROFILE_DIR")
    if configured_path:
        return Path(configured_path).expanduser()
    return data_dir() / "whatsapp-profile"
