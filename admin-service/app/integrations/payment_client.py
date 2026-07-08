"""HTTP client for the Payment Service."""
from __future__ import annotations

from typing import Any

from app.core.config import settings
from app.integrations.base_client import BaseServiceClient


class PaymentServiceClient(BaseServiceClient):
    base_url = settings.PAYMENT_SERVICE_URL

    async def get_payment_stats(self) -> dict[str, Any]:
        """Aggregate revenue data for dashboard."""
        return await self.get("/api/v1/payments/stats")

    async def get_current_provider(self) -> str:
        """Ask the payment service which provider it is currently using."""
        data = await self.get("/api/v1/payments/provider")
        return (data or {}).get("provider", "unknown")

    async def update_provider(self, provider: str) -> dict[str, Any]:
        """
        Tell the payment service to switch providers at runtime.
        The payment service reads PAYMENT_PROVIDER from its own DB config.
        """
        return await self.patch("/api/v1/payments/provider", json={"provider": provider})
