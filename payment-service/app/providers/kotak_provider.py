"""
Kotak Payment Provider.

Fallback payment gateway implementation.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from app.providers.base import (
    PaymentProvider,
    PaymentResult,
    RefundResult,
    SettlementResult,
    WebhookResult,
)


class KotakProvider(PaymentProvider):

    def get_name(self) -> str:
        return "kotak"

    async def create_payment(
        self,
        data: dict[str, Any],
    ) -> PaymentResult:
        """
        TODO:
        Integrate Kotak Payment Gateway API.
        """
        raise NotImplementedError(
            "Kotak payment creation is not implemented."
        )

    async def verify_webhook(
        self,
        headers: dict[str, str],
        body: bytes,
    ) -> WebhookResult:
        """
        TODO:
        Verify Kotak webhook signature.
        """
        raise NotImplementedError(
            "Kotak webhook verification is not implemented."
        )

    async def refund(
        self,
        payment_id: str,
        amount: Decimal,
        reason: str | None = None,
    ) -> RefundResult:
        """
        TODO:
        Integrate Kotak Refund API.
        """
        raise NotImplementedError(
            "Kotak refunds are not implemented."
        )

    async def fetch_settlements(
        self,
    ) -> list[SettlementResult]:
        """
        TODO:
        Download settlement report from Kotak.
        """
        raise NotImplementedError(
            "Kotak settlements are not implemented."
        )

    async def health_check(self) -> bool:
        """
        Check gateway availability.
        """
        return False