"""Meta / WhatsApp Business API provider — placeholder implementation.

Activate by:
  1. Set WHATSAPP_PROVIDER=meta in .env.
  2. Set META_WHATSAPP_ACCESS_TOKEN and META_WHATSAPP_PHONE_NUMBER_ID.
  3. Implement send_message() below using the Graph API.

Docs: https://developers.facebook.com/docs/whatsapp/cloud-api/
"""
from __future__ import annotations

import logging

import httpx

from app.core.config import settings
from app.providers.base import MessageResult, WhatsAppProvider

logger = logging.getLogger(__name__)

GRAPH_API_URL = "https://graph.facebook.com/v18.0/{phone_number_id}/messages"


class MetaWhatsAppProvider(WhatsAppProvider):
    """Meta WhatsApp Business Cloud API adapter."""

    def get_name(self) -> str:
        return "meta"

    async def send_message(self, phone: str, message: str) -> MessageResult:
        if not (settings.META_WHATSAPP_ACCESS_TOKEN and settings.META_WHATSAPP_PHONE_NUMBER_ID):
            logger.warning("Meta WhatsApp credentials not set — returning stub result")
            return MessageResult(
                provider=self.get_name(),
                external_message_id=f"stub_meta_{phone}",
                success=True,
            )

        url = GRAPH_API_URL.format(phone_number_id=settings.META_WHATSAPP_PHONE_NUMBER_ID)
        payload = {
            "messaging_product": "whatsapp",
            "to": phone.lstrip("+"),
            "type": "text",
            "text": {"preview_url": False, "body": message},
        }

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(
                    url,
                    json=payload,
                    headers={"Authorization": f"Bearer {settings.META_WHATSAPP_ACCESS_TOKEN}"},
                )
                response.raise_for_status()
                data = response.json()
                msg_id = (data.get("messages") or [{}])[0].get("id", "")
                return MessageResult(
                    provider=self.get_name(),
                    external_message_id=msg_id,
                    success=True,
                )
        except httpx.HTTPStatusError as exc:
            error_body = exc.response.text
            logger.error("Meta send failed (%s): %s", exc.response.status_code, error_body)
            return MessageResult(
                provider=self.get_name(),
                external_message_id="",
                success=False,
                error=error_body,
            )
        except Exception as exc:
            logger.error("Meta unexpected error: %s", exc, exc_info=True)
            return MessageResult(
                provider=self.get_name(),
                external_message_id="",
                success=False,
                error=str(exc),
            )
