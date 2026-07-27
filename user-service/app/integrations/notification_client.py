"""Thin async HTTP client for the Notification Service.

The Notification Service exposes a fire-and-forget trigger endpoint
(`POST /api/v1/notifications/trigger`) that persists the message via an
outbox pattern and delivers it asynchronously. We call it for:
  - OTP delivery (SMS/Email)
  - Password reset emails
  - Login alerts

Failures here are logged but never raised to the caller — a notification
failure must not fail the underlying auth/profile operation. Celery tasks
that call this client get automatic retries on transient failures.
"""
from __future__ import annotations

import logging
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

_TRIGGER_PATH = "/api/v1/notifications/trigger"


class NotificationClient:
    def __init__(self, base_url: str | None = None) -> None:
        self.base_url = base_url or settings.NOTIFICATION_SERVICE_URL

    async def trigger(
        self,
        *,
        event_type: str,
        channel: str,
        recipient: str,
        body: str,
        subject: str | None = None,
        payload: dict[str, Any] | None = None,
        correlation_id: str | None = None,
        priority: int = 5,
    ) -> bool:
        """Fire a notification. Returns True if accepted, False otherwise."""
        url = f"{self.base_url}{_TRIGGER_PATH}"
        body_payload = {
            "event_type": event_type,
            "channel": channel,
            "recipient": recipient,
            "subject": subject,
            "body": body,
            "payload": payload or {},
            "correlation_id": correlation_id,
            "priority": priority,
        }
        headers = {"X-Internal-Service-Token": settings.INTERNAL_SERVICE_TOKEN}
        try:
            async with httpx.AsyncClient(timeout=settings.SERVICE_HTTP_TIMEOUT_SECONDS) as client:
                response = await client.post(url, json=body_payload, headers=headers)
                response.raise_for_status()
            return True
        except httpx.HTTPError as exc:
            logger.warning("Notification trigger failed (event=%s): %s", event_type, exc)
            return False

    async def send_otp(self, *, identifier: str, channel: str, code: str) -> bool:
        return await self.trigger(
            event_type="user.otp_login",
            channel=channel,
            recipient=identifier,
            subject="Your Nutmeals login code",
            body=f"Your one-time login code is {code}. It expires in a few minutes.",
            payload={"code_length": len(code)},
        )

    async def send_password_reset(self, *, email: str, reset_link: str) -> bool:
        return await self.trigger(
            event_type="user.password_reset",
            channel="email",
            recipient=email,
            subject="Reset your Nutmeals password",
            body=f"We received a request to reset your password. Use this link to continue: {reset_link}",
            payload={"reset_link": reset_link},
            priority=3,
        )

    async def send_login_alert(self, *, email: str, ip_address: str | None) -> bool:
        return await self.trigger(
            event_type="user.login_alert",
            channel="email",
            recipient=email,
            subject="New sign-in to your Nutmeals account",
            body=f"Your account was just accessed{f' from {ip_address}' if ip_address else ''}. "
            "If this wasn't you, please reset your password immediately.",
            payload={"ip_address": ip_address},
            priority=6,
        )


notification_client = NotificationClient()
