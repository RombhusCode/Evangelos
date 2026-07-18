"""Message collection interfaces for Evangelos."""

from collector.auth import (
    WhatsAppAuthenticationError,
    WhatsAppAuthenticator,
    WhatsAppAuthConfig,
)
from collector.whatsapp import (
    ChatSummary,
    WhatsAppChatCollector,
    WhatsAppDiscoveryError,
    discover_chats,
    fetch_messages,
    sync,
)

__all__ = [
    "ChatSummary",
    "WhatsAppChatCollector",
    "WhatsAppAuthenticationError",
    "WhatsAppAuthenticator",
    "WhatsAppAuthConfig",
    "WhatsAppDiscoveryError",
    "discover_chats",
    "fetch_messages",
    "sync",
]
