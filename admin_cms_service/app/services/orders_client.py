"""Client for the upstream Orders service."""
import uuid
from datetime import date

from app.config import get_settings
from app.services.base_client import BaseServiceClient

settings = get_settings()


class OrdersServiceClient(BaseServiceClient):
    def __init__(self) -> None:
        super().__init__(base_url=settings.orders_service_url)

    async def get_order(self, order_id: uuid.UUID) -> dict:
        return await self.get(f"/internal/v1/orders/{order_id}")

    async def get_order_metrics(self, period_start: date, period_end: date) -> dict:
        """Fetch order-count / GMV / AOV metrics for analytics aggregation."""
        return await self.get(
            "/internal/v1/metrics",
            params={"period_start": period_start.isoformat(), "period_end": period_end.isoformat()},
        )

    async def get_customer_cohort_metrics(self, period_start: date, period_end: date) -> dict:
        """Fetch new-vs-repeat customer counts for churn/repeat-rate KPIs."""
        return await self.get(
            "/internal/v1/customers/cohorts",
            params={"period_start": period_start.isoformat(), "period_end": period_end.isoformat()},
        )


def get_orders_client() -> OrdersServiceClient:
    return OrdersServiceClient()
