"""
Thin async HTTP client for the Orders/Payments microservice.

Finance is deliberately decoupled from the Orders DB (separate service,
separate database per the platform's microservices architecture). To
reconcile a settlement against "what we expected to be paid", we call the
Orders service's internal API rather than joining across databases.
"""

import httpx
from pydantic import BaseModel

from app.core.config import get_settings

settings = get_settings()


class OrderPaymentExpectation(BaseModel):
    order_id: str
    expected_amount_minor: int
    currency: str = "INR"
    status: str


class OrderServiceClient:
    def __init__(self, base_url: str | None = None, timeout: float = 5.0):
        self.base_url = base_url or "http://orders-service.internal:8000"
        self.timeout = timeout

    async def get_expected_payment(self, order_reference: str) -> OrderPaymentExpectation | None:
        """
        Fetches the expected paid amount for an order from the Orders
        service. Returns None if the order can't be found (treated as an
        unmatched settlement upstream).
        """
        url = f"{self.base_url}/internal/v1/orders/{order_reference}/payment-expectation"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url)
            if response.status_code == 404:
                return None
            response.raise_for_status()
            return OrderPaymentExpectation.model_validate(response.json())
        except httpx.HTTPError:
            # Network/timeout errors surface as "unmatched" rather than
            # crashing the whole reconciliation run; they get flagged for
            # manual review and can be retried on the next run.
            return None
