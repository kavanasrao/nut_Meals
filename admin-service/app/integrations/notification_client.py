"""HTTP client for the Notification Service."""
from __future__ import annotations

from typing import Any

from app.core.config import settings
from app.integrations.base_client import BaseServiceClient


class NotificationServiceClient(BaseServiceClient):
    base_url = settings.NOTIFICATION_SERVICE_URL

    async def list_logs(
        self,
        *,
        channel: str | None = None,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        if channel:
            params["channel"] = channel
        if status:
            params["status"] = status
        return await self.get("/api/v1/notifications/logs", params=params)

    async def send_manual(self, channel: str, recipient: str, message: str) -> dict[str, Any]:
        return await self.post(
            "/api/v1/notifications/send",
            json={"channel": channel, "recipient": recipient, "message": message},
        )

    async def update_provider(self, provider: str) -> dict[str, Any]:
        return await self.patch(
            "/api/v1/notifications/provider",
            json={"provider": provider},
        )

    async def get_current_provider(self) -> str:
        data = await self.get("/api/v1/notifications/provider")
        return (data or {}).get("provider", "unknown")
