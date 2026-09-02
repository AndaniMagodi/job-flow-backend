"""Outbound notification channels.

One interface so the alerting code never knows how a message is delivered.
WhatsApp is the channel that matters most for a South African audience — it is
where people actually are, and it costs the recipient nothing to receive.
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass


class NotificationError(Exception):
    pass


class ChannelUnavailableError(NotificationError):
    """The channel has no credentials configured."""


@dataclass
class Message:
    """One notification, addressed and ready to send."""

    to: str
    body: str
    #: Optional link the recipient should be able to tap.
    url: str | None = None


# South African mobile numbers, accepted in the shapes people actually type:
# 0821234567, 082 123 4567, +27 82 123 4567, 27821234567.
_SA_MOBILE = re.compile(r"^(?:\+?27|0)(6|7|8)\d{8}$")


def normalise_sa_mobile(number: str) -> str:
    """Return a number in the E.164 form messaging APIs expect (27821234567).

    Raises ValueError for anything that isn't a plausible SA mobile number, so
    a typo fails at save time rather than silently never delivering.
    """
    digits = re.sub(r"[\s()-]", "", number or "")

    if not _SA_MOBILE.match(digits):
        raise ValueError(
            "Enter a South African mobile number, e.g. 082 123 4567"
        )

    digits = digits.lstrip("+")
    if digits.startswith("0"):
        digits = "27" + digits[1:]

    return digits


class NotificationChannel(ABC):
    """Interface every delivery mechanism implements."""

    name: str = "base"

    @abstractmethod
    def send(self, message: Message) -> None:
        """Deliver one message, or raise NotificationError."""

    def is_configured(self) -> bool:
        return True

    def validate_destination(self, destination: str) -> str:
        """Normalise and check an address for this channel."""
        return destination
