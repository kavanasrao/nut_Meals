"""HTTP client for the Delivery Service."""
from __future__ import annotations

from typing import Any

from app.core.config import settings
from app.integrations.base_client import BaseServiceClient


class DeliveryServiceClient(BaseServiceClient):
    base_url = settings.DELIVERY_SERVICE_URL

    async def list_options(self) -> list[dict[str, Any]]:
        return await self.get("/api/v1/delivery/options/all")

    async def create_option(self, data: dict[str, Any]) -> dict[str, Any]:
        return await self.post("/api/v1/delivery/options", json=data)

    async def update_option(self, option_id: str, data: dict[str, Any]) -> dict[str, Any]:
        return await self.patch(f"/api/v1/delivery/options/{option_id}", json=data)

    async def delete_option(self, option_id: str) -> None:
        await self.delete(f"/api/v1/delivery/options/{option_id}")

    async def get_active_deliveries_count(self) -> int:
        data = await self.get("/api/v1/delivery/stats")
        return int((data or {}).get("active", 0))
