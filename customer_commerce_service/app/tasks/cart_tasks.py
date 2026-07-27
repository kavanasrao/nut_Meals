"""Abandoned cart recovery task."""
import asyncio
import logging
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy import select, update

from app.core.config import settings
from app.db.session import AsyncSessionFactory
from app.models.cart import Cart
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


async def _find_and_notify_abandoned_carts() -> int:
    """
    Finds carts inactive for ABANDONED_CART_HOURS that haven't had
    a recovery email sent yet, notifies the Notification Service, and
    marks them as emailed.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=settings.ABANDONED_CART_HOURS)

    async with AsyncSessionFactory() as db:
        result = await db.execute(
            select(Cart).where(
                Cart.is_active == True,
                Cart.last_activity_at < cutoff,
                Cart.recovery_email_sent_at == None,  # noqa: E711
            )
        )
        abandoned = result.scalars().all()

        if not abandoned:
            return 0

        cart_ids = [c.id for c in abandoned]
        payloads = [
            {"user_id": str(c.user_id), "cart_id": str(c.id)}
            for c in abandoned
        ]

        # Fire and forget to Notification Service
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                await client.post(
                    f"{settings.NOTIFICATION_SERVICE_URL}/internal/abandoned-cart",
                    json={"carts": payloads},
                )
        except Exception as exc:
            logger.warning("Notification service unavailable: %s", exc)

        # Mark sent
        await db.execute(
            update(Cart)
            .where(Cart.id.in_(cart_ids))
            .values(recovery_email_sent_at=datetime.now(timezone.utc))
        )
        await db.commit()
        return len(abandoned)


@celery_app.task(name="app.tasks.cart_tasks.send_abandoned_cart_emails", bind=True, max_retries=3)
def send_abandoned_cart_emails(self) -> dict:
    """Celery beat entry point — runs the async coroutine synchronously."""
    try:
        count = asyncio.get_event_loop().run_until_complete(
            _find_and_notify_abandoned_carts()
        )
        logger.info("Abandoned cart emails queued: %d", count)
        return {"processed": count}
    except Exception as exc:
        logger.exception("Error in abandoned cart task")
        raise self.retry(exc=exc, countdown=300)
