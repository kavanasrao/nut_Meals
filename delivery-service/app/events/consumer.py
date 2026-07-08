"""Redis consumer — listens for ORDER_CREATED events and auto-assigns delivery."""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from app.core.db import AsyncSessionLocal
from app.core.redis import get_redis
from app.events.events import EventType
from app.events.publisher import EventPublisher
from app.services.delivery_service import DeliveryService

logger = logging.getLogger(__name__)


async def _handle_order_created(payload: dict[str, Any]) -> None:
    async with AsyncSessionLocal() as db:
        svc = DeliveryService(db)
        assignment = await svc.assign_delivery(payload)

        # Publish DELIVERY_ASSIGNED event for Notification service
        await EventPublisher.publish(
            EventType.DELIVERY_ASSIGNED,
            {
                "order_id": payload.get("order_id"),
                "user_id": payload.get("user_id"),
                "rider_name": assignment.rider_name,
                "rider_phone": assignment.rider_phone,
                "eta_minutes": assignment.eta_minutes,
                "phone": payload.get("phone"),  # forwarded for notification
            },
        )


async def run_consumer() -> None:
    """Listen for ORDER_CREATED events and trigger delivery assignment."""
    channel = EventType.ORDER_CREATED.value
    logger.info("Delivery consumer subscribing to channel: %s", channel)

    redis = await get_redis()
    pubsub = redis.pubsub()
    await pubsub.subscribe(channel)

    logger.info("Delivery consumer listening...")
    try:
        async for raw_message in pubsub.listen():
            if raw_message["type"] != "message":
                continue
            try:
                envelope = json.loads(raw_message["data"])
                payload = envelope.get("payload", {})
                asyncio.create_task(_handle_order_created(payload))
            except Exception as exc:
                logger.error("Delivery consumer error: %s", exc, exc_info=True)
    except asyncio.CancelledError:
        logger.info("Delivery consumer cancelled")
    finally:
        await pubsub.unsubscribe(channel)
