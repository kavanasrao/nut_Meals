"""Clients for the Payments and Inventory services, used by analytics aggregation."""
from datetime import date

from app.config import get_settings
from app.services.base_client import BaseServiceClient

settings = get_settings()


class PaymentsServiceClient(BaseServiceClient):
    def __init__(self) -> None:
        super().__init__(base_url=settings.payments_service_url)

    async def get_conversion_metrics(self, period_start: date, period_end: date) -> dict:
        """Fetch visitor/checkout/conversion funnel data."""
        return await self.get(
            "/internal/v1/funnel",
            params={"period_start": period_start.isoformat(), "period_end": period_end.isoformat()},
        )


class InventoryServiceClient(BaseServiceClient):
    def __init__(self) -> None:
        super().__init__(base_url=settings.inventory_service_url)

    async def get_low_stock_count(self) -> dict:
        return await self.get("/internal/v1/stock/low-stock-count")


def get_payments_client() -> PaymentsServiceClient:
    return PaymentsServiceClient()


def get_inventory_client() -> InventoryServiceClient:
    return InventoryServiceClient()
