"""Client for the upstream Finance service."""
from datetime import date

from app.config import get_settings
from app.services.base_client import BaseServiceClient

settings = get_settings()


class FinanceServiceClient(BaseServiceClient):
    def __init__(self) -> None:
        super().__init__(base_url=settings.finance_service_url)

    async def get_revenue_expense_summary(self, period_start: date, period_end: date) -> dict:
        """Fetch raw revenue/expense/P&L figures for a period from Finance service."""
        return await self.get(
            "/internal/v1/summary",
            params={"period_start": period_start.isoformat(), "period_end": period_end.isoformat()},
        )

    async def get_expense_breakdown(self, period_start: date, period_end: date) -> dict:
        """Fetch expense-category breakdown for a period."""
        return await self.get(
            "/internal/v1/expenses/breakdown",
            params={"period_start": period_start.isoformat(), "period_end": period_end.isoformat()},
        )


def get_finance_client() -> FinanceServiceClient:
    return FinanceServiceClient()
