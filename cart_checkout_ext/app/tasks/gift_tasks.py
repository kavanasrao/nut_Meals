"""Celery tasks for gift-order notifications (e.g. emailing the recipient
that a gift is on the way)."""
import logging

import httpx
from celery import shared_task
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.gift import GiftOrder

logger = logging.getLogger(__name__)
settings = get_settings()

_sync_engine = create_engine(settings.DATABASE_URL_SYNC, pool_pre_ping=True)


@shared_task(
    name="app.tasks.gift_tasks.send_gift_notification",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
)
def send_gift_notification(self, gift_order_id: str) -> dict:
    """Send a notification to the gift recipient via the Notifications
    service. Marks `notification_sent` once delivery is accepted upstream."""
    with Session(_sync_engine) as session:
        gift_order = session.execute(
            select(GiftOrder).where(GiftOrder.id == gift_order_id)
        ).scalar_one_or_none()

        if gift_order is None:
            logger.warning("gift order %s not found, skipping notification", gift_order_id)
            return {"sent": False, "reason": "not_found"}

        if gift_order.notification_sent:
            return {"sent": True, "reason": "already_sent"}

        try:
            resp = httpx.post(
                f"{settings.NOTIFICATIONS_SERVICE_URL}/v1/notifications/gift-order",
                json={
                    "gift_order_id": str(gift_order.id),
                    "recipient_email": gift_order.recipient_email,
                    "recipient_name": gift_order.recipient_name,
                    "gift_message": gift_order.gift_message,
                    "scheduled_delivery_date": (
                        gift_order.scheduled_delivery_date.isoformat()
                        if gift_order.scheduled_delivery_date
                        else None
                    ),
                },
                timeout=10.0,
            )
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            logger.warning("gift notification failed for %s: %s", gift_order_id, exc)
            raise self.retry(exc=exc)

        gift_order.notification_sent = True
        session.commit()
        return {"sent": True}
