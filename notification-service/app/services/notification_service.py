"""Notification Service — business logic layer.

Sends WhatsApp messages via the configured provider with retry logic.
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.notification import Notification, NotificationStatus
from app.providers.factory import get_whatsapp_provider
from app.services.templates import build_message

logger = logging.getLogger(__name__)

# Parse retry delays from config
_RETRY_DELAYS: list[int] = [
    int(s) for s in settings.NOTIFICATION_RETRY_DELAYS.split(",") if s.strip().isdigit()
]


class NotificationService:
    """Handles sending WhatsApp notifications with retries and persistence."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.provider = get_whatsapp_provider()

    async def send_event_notification(
        self,
        event_type: str,
        payload: dict[str, Any],
    ) -> None:
        """
        Build a WhatsApp message from the event payload and send it.
        The payload must contain a 'phone' key for the recipient.
        """
        phone = payload.get("phone") or payload.get("user_phone")
        if not phone:
            logger.warning("No phone in event payload for %s — skipping", event_type)
            return

        message = build_message(event_type, payload)
        if not message:
            logger.info("No template registered for event_type=%s — skipping", event_type)
            return

        await self._send_with_retry(
            phone=phone,
            message=message,
            event_type=event_type,
            event_payload=payload,
        )

    async def _send_with_retry(
        self,
        phone: str,
        message: str,
        event_type: str,
        event_payload: dict[str, Any],
    ) -> None:
        """Attempt to send a WhatsApp message, persisting result and retrying on failure."""
        notification = Notification(
            id=uuid.uuid4(),
            channel="whatsapp",
            provider=self.provider.get_name(),
            recipient_phone=phone,
            message_body=message,
            event_type=event_type,
            event_payload=event_payload,
            status=NotificationStatus.PENDING,
        )
        self.db.add(notification)
        await self.db.commit()
        await self.db.refresh(notification)

        for attempt in range(settings.NOTIFICATION_MAX_RETRIES + 1):
            result = await self.provider.send_message(phone, message)

            if result.success:
                notification.status = NotificationStatus.SENT
                notification.external_message_id = result.external_message_id
                await self.db.commit()
                logger.info(
                    "WhatsApp sent to %s [%s] attempt=%d msg_id=%s",
                    phone, event_type, attempt + 1, result.external_message_id,
                )
                return

            # Send failed
            notification.retry_count = attempt + 1
            notification.last_error = result.error
            notification.status = NotificationStatus.RETRYING

            if attempt < settings.NOTIFICATION_MAX_RETRIES:
                delay = _RETRY_DELAYS[attempt] if attempt < len(_RETRY_DELAYS) else 600
                logger.warning(
                    "WhatsApp send failed (attempt %d/%d) to %s — retrying in %ds. Error: %s",
                    attempt + 1, settings.NOTIFICATION_MAX_RETRIES + 1, phone, delay, result.error,
                )
                await self.db.commit()
                await asyncio.sleep(delay)
            else:
                notification.status = NotificationStatus.FAILED
                await self.db.commit()
                logger.error(
                    "WhatsApp send permanently failed to %s for event=%s after %d attempts",
                    phone, event_type, attempt + 1,
                )
