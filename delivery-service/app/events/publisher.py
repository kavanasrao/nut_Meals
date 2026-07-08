"""Redis Pub/Sub event publisher for the Delivery Service."""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from app.core.redis import get_redis
from app.events.events import EventType

logger = logging.getLogger(__name__)


class EventPublisher:
    @staticmethod
    async def publish(
        event_type: EventType,
        payload: dict[str, Any],
        *,
        channel: str | None = None,
    ) -> None:
        redis = await get_redis()
        event = {
            "event_id": str(uuid.uuid4()),
            "event_type": event_type.value,
            "source": "delivery-service",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": payload,
        }
        target_channel = channel or event_type.value
        try:
            await redis.publish(target_channel, json.dumps(event))
            logger.info("Published %s to %s", event_type.value, target_channel)
        except Exception as exc:
            logger.error("Failed to publish %s: %s", event_type.value, exc, exc_info=True)
            raise
