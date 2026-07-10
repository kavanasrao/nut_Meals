"""Celery tasks for subscription renewal billing and renewal-reminder
notifications. Uses a synchronous DB session/HTTP client since Celery
workers here run outside the FastAPI async event loop.
"""
import logging
from datetime import datetime, timedelta, timezone

import httpx
from celery import shared_task
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.subscription import Subscription, SubscriptionStatus

logger = logging.getLogger(__name__)
settings = get_settings()

_sync_engine = create_engine(settings.DATABASE_URL_SYNC, pool_pre_ping=True)

MAX_RENEWAL_ATTEMPTS = 3


@shared_task(name="app.tasks.subscription_tasks.process_due_renewals")
def process_due_renewals() -> dict:
    """Find all active subscriptions whose next_renewal_date has passed,
    attempt to bill them via the Payments service, and advance/roll back
    state accordingly. Runs hourly via Celery beat."""
    now = datetime.now(timezone.utc)
    processed, succeeded, failed = 0, 0, 0

    with Session(_sync_engine) as session:
        due_subs = session.execute(
            select(Subscription).where(
                Subscription.status == SubscriptionStatus.ACTIVE,
                Subscription.next_renewal_date <= now,
            )
        ).scalars().all()

        for sub in due_subs:
            processed += 1
            ok = _charge_subscription(sub)
            if ok:
                sub.last_renewed_at = now
                sub.failed_renewal_attempts = 0
                sub.renewal_notice_sent = False
                sub.next_renewal_date = _advance(sub, now)
                succeeded += 1
            else:
                sub.failed_renewal_attempts += 1
                if sub.failed_renewal_attempts >= MAX_RENEWAL_ATTEMPTS:
                    sub.status = SubscriptionStatus.PAST_DUE
                failed += 1
        session.commit()

    logger.info("renewal sweep: processed=%s succeeded=%s failed=%s", processed, succeeded, failed)
    return {"processed": processed, "succeeded": succeeded, "failed": failed}


def _advance(sub: Subscription, now: datetime) -> datetime:
    from dateutil.relativedelta import relativedelta

    if sub.frequency.value == "weekly":
        return now + timedelta(weeks=1)
    return now + relativedelta(months=1)


def _charge_subscription(sub: Subscription) -> bool:
    try:
        resp = httpx.post(
            f"{settings.PAYMENTS_SERVICE_URL}/v1/charges/recurring",
            json={
                "payment_method_token": sub.payment_method_token,
                "amount": float(sub.price_amount),
                "currency": sub.currency,
            },
            timeout=10.0,
        )
        resp.raise_for_status()
        return True
    except httpx.HTTPError as exc:
        logger.warning("renewal charge failed for subscription=%s: %s", sub.id, exc)
        return False


@shared_task(name="app.tasks.subscription_tasks.send_upcoming_renewal_notices")
def send_upcoming_renewal_notices() -> dict:
    """Notify customers whose subscription will renew within
    RENEWAL_NOTICE_DAYS, so they can pause/cancel/update payment first."""
    now = datetime.now(timezone.utc)
    window_end = now + timedelta(days=settings.RENEWAL_NOTICE_DAYS)
    notified = 0

    with Session(_sync_engine) as session:
        upcoming = session.execute(
            select(Subscription).where(
                Subscription.status == SubscriptionStatus.ACTIVE,
                Subscription.next_renewal_date <= window_end,
                Subscription.next_renewal_date > now,
                Subscription.renewal_notice_sent.is_(False),
            )
        ).scalars().all()

        for sub in upcoming:
            _send_renewal_reminder.delay(str(sub.id), sub.next_renewal_date.isoformat())
            sub.renewal_notice_sent = True
            notified += 1
        session.commit()

    logger.info("renewal notices queued: %s", notified)
    return {"notified": notified}


@shared_task(
    name="app.tasks.subscription_tasks._send_renewal_reminder",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
)
def _send_renewal_reminder(self, subscription_id: str, renewal_date_iso: str) -> None:
    try:
        resp = httpx.post(
            f"{settings.NOTIFICATIONS_SERVICE_URL}/v1/notifications/subscription-renewal",
            json={"subscription_id": subscription_id, "renewal_date": renewal_date_iso},
            timeout=10.0,
        )
        resp.raise_for_status()
    except httpx.HTTPError as exc:
        logger.warning("renewal reminder failed for subscription=%s: %s", subscription_id, exc)
        raise self.retry(exc=exc)
