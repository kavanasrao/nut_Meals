"""
Stripe payment provider.

This is currently a placeholder implementation.
Activate by:

1. pip install stripe
2. PAYMENT_PROVIDER=stripe
3. Configure STRIPE_SECRET_KEY and STRIPE_WEBHOOK_SECRET
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


class StripeProvider(PaymentProvider):

    def get_name(self) -> str:
        return "stripe"

    async def create_payment(
        self,
        data: dict[str, Any],
    ) -> PaymentResult:
        raise NotImplementedError(
            "Stripe payment creation is not implemented."
        )

    async def verify_webhook(
        self,
        headers: dict[str, str],
        body: bytes,
    ) -> WebhookResult:
        raise NotImplementedError(
            "Stripe webhook verification is not implemented."
        )

    async def refund(
        self,
        payment_id: str,
        amount: Decimal,
        reason: str | None = None,
    ) -> RefundResult:
        raise NotImplementedError(
            "Stripe refunds are not implemented."
        )

    async def fetch_settlements(
        self,
    ) -> list[SettlementResult]:
        raise NotImplementedError(
            "Stripe settlements are not implemented."
        )

    async def health_check(self) -> bool:
        return False
