"""HTTP client for the Order Service."""
from __future__ import annotations

from typing import Any

from app.core.config import settings
from app.integrations.base_client import BaseServiceClient


class OrderServiceClient(BaseServiceClient):
    base_url = settings.ORDER_SERVICE_URL

    async def list_orders(self, *, limit: int = 50, offset: int = 0, status: str | None = None) -> dict[str, Any]:
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        if status:
            params["status"] = status
        return await self.get("/api/v1/orders", params=params)

    async def get_order(self, order_id: str) -> dict[str, Any]:
        return await self.get(f"/api/v1/orders/{order_id}")

    async def update_order_status(self, order_id: str, new_status: str) -> dict[str, Any]:
        return await self.patch(
            f"/api/v1/orders/{order_id}/status",
            json={"status": new_status},
        )

    async def get_order_stats(self) -> dict[str, Any]:
        """Return aggregated stats for the dashboard."""
        return await self.get("/api/v1/orders/stats")
