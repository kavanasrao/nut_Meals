import hashlib
import hmac
import json

import httpx

from app.channels.base import BaseChannel, ChannelSendError
from app.config import get_settings
from app.models.message import Message

settings = get_settings()


class WebhookChannel(BaseChannel):
    """Generic outbound webhook delivery for external systems (partners, ERPs, etc.)."""

    name = "webhook"

    async def send(self, message: Message) -> dict:
        url = message.recipient  # for webhooks, `recipient` holds the target URL
        payload = message.payload or {"body": message.body}
        body_bytes = json.dumps(payload).encode()

        signature = hmac.new(settings.jwt_secret.encode(), body_bytes, hashlib.sha256).hexdigest()
        headers = {"Content-Type": "application/json", "X-NutMeals-Signature": signature}

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(url, content=body_bytes, headers=headers)
        except httpx.RequestError as exc:
            raise ChannelSendError(f"Webhook network error: {exc}", retryable=True) from exc

        if resp.status_code >= 500:
            raise ChannelSendError(f"Webhook server error {resp.status_code}", retryable=True)
        if resp.status_code >= 400:
            raise ChannelSendError(f"Webhook client error {resp.status_code}", retryable=False)

        return {"status_code": resp.status_code}
