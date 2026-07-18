"""Message collection interfaces for Evangelos."""

from collector.auth import (
    WhatsAppAuthenticationError,
    WhatsAppAuthenticator,
    WhatsAppAuthConfig,
)
from collector.whatsapp import fetch_messages, sync

__all__ = [
    "WhatsAppAuthenticationError",
    "WhatsAppAuthenticator",
    "WhatsAppAuthConfig",
    "fetch_messages",
    "sync",
]
