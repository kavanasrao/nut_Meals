"""Redis Pub/Sub event publisher for the Order Service.

Events are published as JSON to named Redis channels corresponding to
the EventType value (e.g. "ORDER_CREATED").  Consumers in other services
subscribe to these channels.
"""
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
    """Publish domain events to Redis Pub/Sub channels."""

    @staticmethod
    async def publish(
        event_type: EventType,
        payload: dict[str, Any],
        *,
        channel: str | None = None,
    ) -> None:
        """
        Serialize and publish an event.

        Args:
            event_type: The event enum value (also used as channel name by default).
            payload: Domain-specific data to include in the event.
            channel: Override the default channel name (event_type.value).
        """
        redis = await get_redis()
        event = {
            "event_id": str(uuid.uuid4()),
            "event_type": event_type.value,
            "source": "order-service",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": payload,
        }
        target_channel = channel or event_type.value

        try:
            subscriber_count = await redis.publish(target_channel, json.dumps(event))
            logger.info(
                "Published event",
                extra={
                    "event_type": event_type.value,
                    "channel": target_channel,
                    "subscribers": subscriber_count,
                    "event_id": event["event_id"],
                },
            )
        except Exception as exc:
            # Log but don't swallow — callers should decide retry strategy
            logger.error(
                "Failed to publish event %s: %s",
                event_type.value,
                exc,
                exc_info=True,
            )
            raise
