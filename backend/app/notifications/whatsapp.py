"""WhatsApp delivery via Meta's Cloud API.

Chosen over email because WhatsApp is where South African job seekers already
are, and a message costs the recipient nothing to receive — which matters when
a lot of your users are on prepaid data.

Setup (all from the Meta Business dashboard):
  1. A WhatsApp Business account with a registered phone number
  2. WHATSAPP_PHONE_NUMBER_ID and WHATSAPP_ACCESS_TOKEN in .env
  3. An APPROVED message template — Meta only allows business-initiated
     messages from a template, and a job alert is always business-initiated.
     WHATSAPP_TEMPLATE_NAME must name it.
"""

from __future__ import annotations

import httpx

from app.core.config import settings
from app.notifications.base import (
    ChannelUnavailableError,
    Message,
    NotificationChannel,
    NotificationError,
    normalise_sa_mobile,
)

API_VERSION = "v21.0"
BASE_URL = "https://graph.facebook.com"


class WhatsAppChannel(NotificationChannel):
    name = "whatsapp"

    def __init__(self):
        self.phone_number_id = settings.whatsapp_phone_number_id
        self.access_token = settings.whatsapp_access_token
        self.template_name = settings.whatsapp_template_name
        self.language = settings.whatsapp_template_language

    def is_configured(self) -> bool:
        return bool(self.phone_number_id and self.access_token and self.template_name)

    def validate_destination(self, destination: str) -> str:
        return normalise_sa_mobile(destination)

    def send(self, message: Message) -> None:
        if not self.is_configured():
            raise ChannelUnavailableError(
                "WhatsApp is not configured — set WHATSAPP_PHONE_NUMBER_ID, "
                "WHATSAPP_ACCESS_TOKEN and WHATSAPP_TEMPLATE_NAME"
            )

        payload = {
            "messaging_product": "whatsapp",
            "to": self.validate_destination(message.to),
            "type": "template",
            "template": {
                "name": self.template_name,
                "language": {"code": self.language},
                "components": [
                    {
                        "type": "body",
                        # The template is expected to take one body variable:
                        # the alert summary. Keep it to one so an approved
                        # template doesn't need re-approval to change wording.
                        "parameters": [{"type": "text", "text": message.body}],
                    }
                ],
            },
        }

        try:
            response = httpx.post(
                f"{BASE_URL}/{API_VERSION}/{self.phone_number_id}/messages",
                json=payload,
                headers={"Authorization": f"Bearer {self.access_token}"},
                timeout=20.0,
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            # Meta puts the actionable reason in the body, not the status line.
            detail = e.response.text[:300]
            raise NotificationError(f"WhatsApp send failed: {detail}") from e
        except httpx.HTTPError as e:
            raise NotificationError(f"WhatsApp request failed: {e}") from e
