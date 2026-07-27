"""Thin async HTTP client for the Order Service.

Used to surface order history on the user's profile (GET /users/me/orders)
without the User Service owning or duplicating order data.
"""
from __future__ import annotations

import logging
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class OrderServiceClient:
    def __init__(self, base_url: str | None = None) -> None:
        self.base_url = base_url or settings.ORDER_SERVICE_URL

    async def get_order_history(self, user_id: str, *, limit: int = 20) -> list[dict[str, Any]]:
        """Fetch this user's recent orders. Returns [] on any downstream failure
        so a flaky Order Service never breaks the user's own profile page."""
        url = f"{self.base_url}/api/v1/orders"
        headers = {"X-Internal-Service-Token": settings.INTERNAL_SERVICE_TOKEN}
        params = {"user_id": user_id, "limit": limit}
        try:
            async with httpx.AsyncClient(timeout=settings.SERVICE_HTTP_TIMEOUT_SECONDS) as client:
                response = await client.get(url, params=params, headers=headers)
                response.raise_for_status()
                data = response.json()
                return data.get("orders", data) if isinstance(data, dict) else data
        except httpx.HTTPError as exc:
            logger.warning("Order history fetch failed for user %s: %s", user_id, exc)
            return []


orders_client = OrderServiceClient()
