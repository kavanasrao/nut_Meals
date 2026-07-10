from __future__ import annotations

"""
Redis Event Publisher for Orders Service.
"""

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
            "source": "orders-service",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": payload,
        }

        target_channel = channel or event_type.value

        try:

            await redis.publish(
                target_channel,
                json.dumps(event),
            )

            logger.info(
                "Published %s",
                event_type.value,
            )

        except Exception:

            logger.exception(
                "Failed publishing %s",
                event_type.value,
            )

            raise