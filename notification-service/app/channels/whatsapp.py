import httpx

from app.channels.base import BaseChannel, ChannelSendError
from app.config import get_settings
from app.models.message import Message

settings = get_settings()


class WhatsAppChannel(BaseChannel):
    """WhatsApp Business Cloud API (RCS-compatible provider follows same contract)."""

    name = "whatsapp"

    async def send(self, message: Message) -> dict:
        url = f"{settings.whatsapp_api_url}/{settings.whatsapp_phone_id}/messages"
        headers = {"Authorization": f"Bearer {settings.whatsapp_token}"}
        body = {
            "messaging_product": "whatsapp",
            "to": message.recipient,
            "type": "text",
            "text": {"body": message.body},
        }

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(url, json=body, headers=headers)
        except httpx.RequestError as exc:
            raise ChannelSendError(f"WhatsApp network error: {exc}", retryable=True) from exc

        if resp.status_code >= 500:
            raise ChannelSendError(f"WhatsApp server error {resp.status_code}", retryable=True)
        if resp.status_code >= 400:
            raise ChannelSendError(f"WhatsApp client error {resp.status_code}: {resp.text}", retryable=False)

        return resp.json()
