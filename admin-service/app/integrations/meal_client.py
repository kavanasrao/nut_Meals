"""HTTP client for the Meal Service."""
from __future__ import annotations

from typing import Any

from app.core.config import settings
from app.integrations.base_client import BaseServiceClient


class MealServiceClient(BaseServiceClient):
    base_url = settings.MEAL_SERVICE_URL

    async def list_meals(self, *, limit: int = 50, offset: int = 0) -> dict[str, Any]:
        return await self.get("/api/v1/meals", params={"limit": limit, "offset": offset})

    async def create_meal(self, data: dict[str, Any]) -> dict[str, Any]:
        return await self.post("/api/v1/meals", json=data)

    async def update_meal(self, meal_id: str, data: dict[str, Any]) -> dict[str, Any]:
        return await self.put(f"/api/v1/meals/{meal_id}", json=data)

    async def delete_meal(self, meal_id: str) -> None:
        await self.delete(f"/api/v1/meals/{meal_id}")
