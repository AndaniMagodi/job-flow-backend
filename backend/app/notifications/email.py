"""Email delivery over SMTP.

SMTP rather than a provider SDK so this works with whatever the project already
has — Gmail with an app password, Resend, SendGrid, Mailgun, or a company relay
— by changing configuration rather than code.
"""

from __future__ import annotations

import smtplib
import ssl
from email.message import EmailMessage

from app.core.config import settings
from app.notifications.base import (
    ChannelUnavailableError,
    Message,
    NotificationChannel,
    NotificationError,
)


class EmailChannel(NotificationChannel):
    name = "email"

    def __init__(self):
        self.host = settings.smtp_host
        self.port = settings.smtp_port
        self.username = settings.smtp_username
        self.password = settings.smtp_password
        self.from_address = settings.smtp_from or settings.smtp_username
        self.from_name = settings.smtp_from_name
        self.use_tls = settings.smtp_use_tls

    def is_configured(self) -> bool:
        return bool(self.host and self.from_address)

    def send(self, message: Message, subject: str = "JobFlow") -> None:
        if not self.is_configured():
            raise ChannelUnavailableError(
                "Email is not configured — set SMTP_HOST, SMTP_USERNAME and "
                "SMTP_PASSWORD"
            )

        email = EmailMessage()
        email["Subject"] = subject
        email["From"] = f"{self.from_name} <{self.from_address}>"
        email["To"] = message.to
        body = message.body if not message.url else f"{message.body}\n\n{message.url}"
        email.set_content(body)

        try:
            context = ssl.create_default_context()
            # Port 465 is implicit TLS; everything else negotiates with STARTTLS.
            if self.port == 465:
                with smtplib.SMTP_SSL(self.host, self.port, context=context, timeout=20) as s:
                    self._authenticate(s)
                    s.send_message(email)
            else:
                with smtplib.SMTP(self.host, self.port, timeout=20) as s:
                    if self.use_tls:
                        s.starttls(context=context)
                    self._authenticate(s)
                    s.send_message(email)
        except smtplib.SMTPAuthenticationError as e:
            raise NotificationError(
                "SMTP rejected the credentials. For Gmail this must be an app "
                "password, not the account password."
            ) from e
        except (smtplib.SMTPException, OSError) as e:
            raise NotificationError(f"Email send failed: {e}") from e

    def _authenticate(self, server: smtplib.SMTP) -> None:
        # A local relay may accept mail without credentials.
        if self.username and self.password:
            server.login(self.username, self.password)
