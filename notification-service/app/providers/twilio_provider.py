"""Twilio WhatsApp provider.

Docs: https://www.twilio.com/docs/whatsapp/api
"""
from __future__ import annotations

import logging

import httpx

from app.core.config import settings
from app.providers.base import MessageResult, WhatsAppProvider

logger = logging.getLogger(__name__)

TWILIO_MESSAGES_URL = "https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"


class TwilioProvider(WhatsAppProvider):
    """Production Twilio WhatsApp adapter."""

    def get_name(self) -> str:
        return "twilio"

    async def send_message(self, phone: str, message: str) -> MessageResult:
        """
        Send a WhatsApp message via Twilio's REST API.

        If credentials are missing, returns a stub result (dev/test mode).
        """
        if not (settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN):
            logger.warning("Twilio credentials not set — returning stub result")
            return MessageResult(
                provider=self.get_name(),
                external_message_id=f"stub_{phone}",
                success=True,
            )

        # Ensure E.164 format without a '+' for the To field
        to_number = f"whatsapp:{phone}" if not phone.startswith("whatsapp:") else phone

        url = TWILIO_MESSAGES_URL.format(account_sid=settings.TWILIO_ACCOUNT_SID)
        payload = {
            "From": settings.TWILIO_WHATSAPP_FROM,
            "To": to_number,
            "Body": message,
        }

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(
                    url,
                    data=payload,
                    auth=(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN),
                )
                response.raise_for_status()
                data = response.json()
                msg_sid = data.get("sid", "")
                logger.info("Twilio message sent: sid=%s to=%s", msg_sid, phone)
                return MessageResult(
                    provider=self.get_name(),
                    external_message_id=msg_sid,
                    success=True,
                )
        except httpx.HTTPStatusError as exc:
            error_body = exc.response.text
            logger.error("Twilio send failed (%s): %s", exc.response.status_code, error_body)
            return MessageResult(
                provider=self.get_name(),
                external_message_id="",
                success=False,
                error=error_body,
            )
        except Exception as exc:
            logger.error("Twilio unexpected error: %s", exc, exc_info=True)
            return MessageResult(
                provider=self.get_name(),
                external_message_id="",
                success=False,
                error=str(exc),
            )
