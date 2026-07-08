"""HTTP client for the User Service."""
from __future__ import annotations

from typing import Any

from app.core.config import settings
from app.integrations.base_client import BaseServiceClient


class UserServiceClient(BaseServiceClient):
    base_url = settings.USER_SERVICE_URL

    async def list_users(self, *, limit: int = 50, offset: int = 0) -> dict[str, Any]:
        return await self.get("/api/v1/users", params={"limit": limit, "offset": offset})

    async def get_user(self, user_id: str) -> dict[str, Any]:
        return await self.get(f"/api/v1/users/{user_id}")

    async def block_user(self, user_id: str) -> dict[str, Any]:
        return await self.patch(f"/api/v1/users/{user_id}/block")

    async def unblock_user(self, user_id: str) -> dict[str, Any]:
        return await self.patch(f"/api/v1/users/{user_id}/unblock")

    async def get_user_count(self) -> int:
        """Return total registered users (used for dashboard stats)."""
        data = await self.get("/api/v1/users/stats")
        return int((data or {}).get("total", 0))
