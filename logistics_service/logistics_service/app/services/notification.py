"""
Thin client for notifying customers via the Messaging service (email, SMS,
WhatsApp). The Logistics Service never sends messages directly; it always
delegates to Messaging so templates/opt-outs/channel routing stay centralized.
"""
import logging

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


async def notify_shipment_status_change(order_id: str, status: str, carrier_awb: str | None) -> None:
    """
    Fire-and-forget style notification. Failures are logged, not raised,
    since a notification failure must never roll back a tracking update.
    """
    payload = {
        "order_id": order_id,
        "event": "shipment_status_update",
        "channels": ["email", "sms", "whatsapp"],
        "context": {"status": status, "carrier_awb": carrier_awb},
    }
    try:
        async with httpx.AsyncClient(base_url=settings.messaging_service_url, timeout=5.0) as client:
            resp = await client.post("/v1/notifications/send", json=payload)
            resp.raise_for_status()
    except httpx.HTTPError as exc:
        logger.error("Failed to notify customer for order %s: %s", order_id, exc)
