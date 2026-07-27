"""Celery tasks — async delivery of OTP codes, password reset emails, and
login alerts via the Notification Service.

Each task wraps an async call to `NotificationClient` (httpx) in
`asyncio.run`, since Celery workers execute tasks synchronously. Tasks retry
on transient failures with exponential-ish fixed backoff; the Notification
Service's own outbox/retry pipeline handles delivery-provider retries, so
these retries only cover the User Service -> Notification Service hop.
"""
from __future__ import annotations

import asyncio
import logging

from celery import shared_task

from app.integrations.notification_client import NotificationClient

logger = logging.getLogger(__name__)


def _run_async(coro):
    return asyncio.run(coro)


@shared_task(
    name="app.tasks.notification_tasks.send_otp_task",
    bind=True,
    max_retries=3,
    default_retry_delay=5,
)
def send_otp_task(self, *, identifier: str, channel: str, code: str) -> bool:
    """Deliver an OTP code via SMS or Email."""
    try:
        client = NotificationClient()
        ok = _run_async(client.send_otp(identifier=identifier, channel=channel, code=code))
        if not ok:
            raise RuntimeError("Notification service rejected OTP delivery")
        return True
    except Exception as exc:  # noqa: BLE001
        logger.exception("OTP delivery failed for %s, retrying: %s", identifier, exc)
        raise self.retry(exc=exc)


@shared_task(
    name="app.tasks.notification_tasks.send_password_reset_email_task",
    bind=True,
    max_retries=3,
    default_retry_delay=10,
)
def send_password_reset_email_task(self, *, email: str, reset_link: str) -> bool:
    """Deliver a password-reset email containing the reset link."""
    try:
        client = NotificationClient()
        ok = _run_async(client.send_password_reset(email=email, reset_link=reset_link))
        if not ok:
            raise RuntimeError("Notification service rejected password-reset email")
        return True
    except Exception as exc:  # noqa: BLE001
        logger.exception("Password reset email failed for %s, retrying: %s", email, exc)
        raise self.retry(exc=exc)


@shared_task(
    name="app.tasks.notification_tasks.send_login_alert_task",
    bind=True,
    max_retries=2,
    default_retry_delay=10,
)
def send_login_alert_task(self, *, email: str, ip_address: str | None) -> bool:
    """Notify the user of a new sign-in (best-effort, low priority)."""
    try:
        client = NotificationClient()
        ok = _run_async(client.send_login_alert(email=email, ip_address=ip_address))
        return ok
    except Exception as exc:  # noqa: BLE001
        logger.warning("Login alert failed for %s: %s", email, exc)
        # Login alerts are non-critical; don't hammer retries indefinitely.
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc)
        return False
