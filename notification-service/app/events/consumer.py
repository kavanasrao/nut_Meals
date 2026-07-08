"""Redis Pub/Sub event consumer for the Notification Service.

Subscribes to ORDER_CREATED, PAYMENT_SUCCESS, and DELIVERY_ASSIGNED channels
and triggers WhatsApp notifications for each event.

Architecture:
  - Runs as a long-lived asyncio task alongside the FastAPI server.
  - Each message is processed in an isolated DB session.
  - A bad event is logged and skipped; it does NOT crash the consumer loop.
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from app.core.config import settings
from app.core.db import AsyncSessionLocal
from app.core.redis import get_redis
from app.services.notification_service import NotificationService

logger = logging.getLogger(__name__)


async def _handle_event(event_type: str, payload: dict[str, Any]) -> None:
    """Process a single event in its own DB session."""
    async with AsyncSessionLocal() as db:
        svc = NotificationService(db)
        await svc.send_event_notification(event_type, payload)


async def run_consumer() -> None:
    """
    Blocking coroutine — subscribes to Redis channels and processes events.

    Call this as a background task on application startup.
    """
    channels = [ch.strip() for ch in settings.SUBSCRIBED_CHANNELS.split(",") if ch.strip()]
    logger.info("Notification consumer subscribing to channels: %s", channels)

    redis = await get_redis()
    pubsub = redis.pubsub()
    await pubsub.subscribe(*channels)

    logger.info("Notification consumer listening...")

    try:
        async for raw_message in pubsub.listen():
            if raw_message["type"] != "message":
                continue

            channel: str = raw_message["channel"]
            data_str: str = raw_message["data"]

            try:
                envelope: dict[str, Any] = json.loads(data_str)
                event_type: str = envelope.get("event_type", channel)
                payload: dict[str, Any] = envelope.get("payload", {})

                logger.info("Received event: %s", event_type)
                asyncio.create_task(_handle_event(event_type, payload))

            except json.JSONDecodeError as exc:
                logger.error("Failed to parse event JSON on channel %s: %s", channel, exc)
            except Exception as exc:
                logger.error("Unexpected error handling event on %s: %s", channel, exc, exc_info=True)

    except asyncio.CancelledError:
        logger.info("Notification consumer task cancelled — shutting down")
    finally:
        await pubsub.unsubscribe(*channels)
        logger.info("Notification consumer unsubscribed")
