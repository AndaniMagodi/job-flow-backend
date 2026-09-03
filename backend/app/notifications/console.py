"""Development channel: log the message instead of sending it.

Lets the whole alert pipeline be exercised end to end without a WhatsApp
Business account, so the scheduling and matching logic can be trusted before
any real delivery is wired up.
"""

from __future__ import annotations

import logging

from app.notifications.base import Message, NotificationChannel

logger = logging.getLogger(__name__)


class ConsoleChannel(NotificationChannel):
    name = "console"

    def send(self, message: Message, subject: str | None = None) -> None:
        # Logged at WARNING, not INFO: this channel means a message was NOT
        # delivered, and uvicorn's default config hides INFO from app loggers —
        # which would make the development fallback silently useless.
        logger.warning(
            "[notification NOT SENT — no channel configured] to=%s%s\n%s%s",
            message.to,
            f"\nsubject={subject}" if subject else "",
            message.body,
            f"\n{message.url}" if message.url else "",
        )
