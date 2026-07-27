"""
Thin async client for the Finance Service. Used to push double-entry
accounting records whenever a vendor ledger entry is created (invoice
booked, payment made, adjustment, etc).

Kept isolated so it can be mocked easily in tests and so retries/circuit
breaking can be added in one place.
"""
import logging
from decimal import Decimal

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class FinanceServiceError(Exception):
    pass


class FinanceServiceClient:
    def __init__(self, base_url: str | None = None, api_key: str | None = None):
        self.base_url = base_url or settings.FINANCE_SERVICE_BASE_URL
        self.api_key = api_key or settings.FINANCE_SERVICE_API_KEY

    async def post_journal_entry(
        self,
        vendor_id: str,
        entry_type: str,
        amount: Decimal,
        source: str,
        reference_id: str | None,
        description: str | None,
    ) -> str:
        """
        Posts a journal entry to Finance Service. Returns the finance-side
        reference id on success.
        """
        payload = {
            "vendor_id": vendor_id,
            "entry_type": entry_type,
            "amount": str(amount),
            "source": source,
            "reference_id": reference_id,
            "description": description,
            "originating_service": "procurement-service",
        }
        headers = {"Authorization": f"Bearer {self.api_key}"}

        try:
            async with httpx.AsyncClient(base_url=self.base_url, timeout=10.0) as client:
                response = await client.post(
                    "/api/v1/journal-entries", json=payload, headers=headers
                )
                response.raise_for_status()
                data = response.json()
                return data["reference_id"]
        except httpx.HTTPError as exc:
            logger.error("Finance service sync failed: %s", exc)
            raise FinanceServiceError(str(exc)) from exc
