"""Transactional email copy.

Plain text on purpose: it renders everywhere, costs almost nothing to receive
on a metered connection, and never lands in spam for having a broken HTML part.
"""

from __future__ import annotations

import logging

from app.core.config import settings
from app.notifications import Message, NotificationError, get_channel

logger = logging.getLogger(__name__)


def _send(to: str, subject: str, body: str) -> bool:
    """Deliver one email. Returns whether it actually went out.

    Never raises: a failure to send must not roll back the registration or
    leak, through an error response, whether an address exists.
    """
    channel = get_channel("email")
    try:
        # The console fallback has no subject parameter.
        if channel.name == "email":
            channel.send(Message(to=to, body=body), subject=subject)
        else:
            channel.send(Message(to=to, body=f"[{subject}]\n{body}"))
        return True
    except NotificationError as e:
        logger.warning("could not email %s: %s", subject, e)
        return False


def send_verification_email(to: str, token: str) -> bool:
    link = f"{settings.frontend_url}/verify-email?token={token}"
    return _send(
        to,
        "Confirm your email — JobFlow",
        "Welcome to JobFlow.\n\n"
        "Confirm your email address to start getting job alerts:\n\n"
        f"{link}\n\n"
        "The link works for 3 days. If you didn't create a JobFlow account, "
        "you can ignore this email.",
    )


def send_password_reset_email(to: str, token: str) -> bool:
    link = f"{settings.frontend_url}/reset-password?token={token}"
    return _send(
        to,
        "Reset your JobFlow password",
        "Someone asked to reset the password for this JobFlow account.\n\n"
        f"{link}\n\n"
        "The link works for 1 hour and can only be used once. If this wasn't "
        "you, ignore this email — your password stays as it is.",
    )
