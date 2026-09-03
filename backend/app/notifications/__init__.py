"""Notification channel registry."""

from app.core.config import settings
from app.notifications.base import (
    ChannelUnavailableError,
    Message,
    NotificationChannel,
    NotificationError,
    normalise_sa_mobile,
)
from app.notifications.console import ConsoleChannel
from app.notifications.email import EmailChannel
from app.notifications.whatsapp import WhatsAppChannel

_REGISTRY: dict[str, type[NotificationChannel]] = {
    WhatsAppChannel.name: WhatsAppChannel,
    EmailChannel.name: EmailChannel,
    ConsoleChannel.name: ConsoleChannel,
}


def get_channel(name: str) -> NotificationChannel:
    """Resolve a channel by name.

    An unconfigured WhatsApp falls back to the console channel when
    NOTIFICATIONS_FALLBACK_TO_CONSOLE is on, so local development doesn't need
    Meta credentials to exercise the pipeline.
    """
    channel_cls = _REGISTRY.get(name)
    if channel_cls is None:
        raise NotificationError(
            f"Unknown channel '{name}'. Known: {', '.join(sorted(_REGISTRY))}"
        )

    channel = channel_cls()
    if not channel.is_configured() and settings.notifications_fallback_to_console:
        return ConsoleChannel()

    return channel


def available_channels() -> list[str]:
    return sorted(n for n, c in _REGISTRY.items() if c().is_configured())


__all__ = [
    "ChannelUnavailableError",
    "ConsoleChannel",
    "EmailChannel",
    "Message",
    "NotificationChannel",
    "NotificationError",
    "WhatsAppChannel",
    "available_channels",
    "get_channel",
    "normalise_sa_mobile",
]
