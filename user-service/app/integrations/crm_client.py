"""Thin async HTTP client for the CRM Service.

Pushes profile/account lifecycle events onto the customer's CRM timeline
(registration, profile updates, address changes) and can fetch the timeline
back for display. Never blocks or fails the caller's request on error.
"""
from __future__ import annotations

import logging
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class CrmServiceClient:
    def __init__(self, base_url: str | None = None) -> None:
        self.base_url = base_url or settings.CRM_SERVICE_URL

    async def push_timeline_event(
        self, *, user_id: str, event_type: str, description: str, metadata: dict[str, Any] | None = None
    ) -> bool:
        url = f"{self.base_url}/api/v1/customer-timeline"
        headers = {"X-Internal-Service-Token": settings.INTERNAL_SERVICE_TOKEN}
        payload = {
            "customer_id": user_id,
            "event_type": event_type,
            "description": description,
            "metadata": metadata or {},
        }
        try:
            async with httpx.AsyncClient(timeout=settings.SERVICE_HTTP_TIMEOUT_SECONDS) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
            return True
        except httpx.HTTPError as exc:
            logger.warning("CRM timeline push failed for user %s: %s", user_id, exc)
            return False

    async def get_timeline(self, user_id: str, *, limit: int = 50) -> list[dict[str, Any]]:
        url = f"{self.base_url}/api/v1/customer-timeline"
        headers = {"X-Internal-Service-Token": settings.INTERNAL_SERVICE_TOKEN}
        params = {"customer_id": user_id, "limit": limit}
        try:
            async with httpx.AsyncClient(timeout=settings.SERVICE_HTTP_TIMEOUT_SECONDS) as client:
                response = await client.get(url, params=params, headers=headers)
                response.raise_for_status()
                data = response.json()
                return data.get("items", data) if isinstance(data, dict) else data
        except httpx.HTTPError as exc:
            logger.warning("CRM timeline fetch failed for user %s: %s", user_id, exc)
            return []


crm_client = CrmServiceClient()
