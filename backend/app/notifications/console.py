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

    def send(self, message: Message) -> None:
        logger.info(
            "[notification] to=%s\n%s%s",
            message.to,
            message.body,
            f"\n{message.url}" if message.url else "",
        )
