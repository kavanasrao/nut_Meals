"""Thin async HTTP client wrapper for calling the Payments microservice.

Kept isolated so it can be mocked easily in tests and so retry/timeout
policy for cross-service calls lives in exactly one place.
"""
import httpx

from app.config import get_settings

settings = get_settings()


class PaymentsClientError(Exception):
    """Raised when the Payments service call fails or returns a non-2xx status."""


class PaymentsClient:
    def __init__(self, base_url: str | None = None, timeout: float = 10.0):
        self.base_url = base_url or settings.PAYMENTS_SERVICE_URL
        self.timeout = timeout

    async def charge_recurring(self, payment_method_token: str, amount: float, currency: str) -> dict:
        """Ask Payments to charge a stored payment method for a subscription renewal."""
        async with httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout) as client:
            try:
                resp = await client.post(
                    "/v1/charges/recurring",
                    json={
                        "payment_method_token": payment_method_token,
                        "amount": amount,
                        "currency": currency,
                    },
                )
                resp.raise_for_status()
                return resp.json()
            except httpx.HTTPError as exc:
                raise PaymentsClientError(str(exc)) from exc
