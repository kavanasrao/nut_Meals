"""
Production Razorpay payment provider.
"""

from __future__ import annotations

import hmac
import hashlib
import json
from decimal import Decimal
from typing import Any

import razorpay

from app.core.config import settings
from app.providers.base import (
    PaymentProvider,
    PaymentResult,
    RefundResult,
    SettlementResult,
    WebhookResult,
)


class RazorpayProvider(PaymentProvider):

    def __init__(self) -> None:
        self.client = razorpay.Client(
            auth=(
                settings.RAZORPAY_KEY_ID,
                settings.RAZORPAY_KEY_SECRET,
            )
        )

    def get_name(self) -> str:
        return "razorpay"

    async def create_payment(
        self,
        data: dict[str, Any],
    ) -> PaymentResult:

        order = self.client.order.create(
            {
                "amount": int(Decimal(data["amount"]) * 100),
                "currency": "INR",
                "receipt": data["order_id"],
                "notes": {
                    "user_id": data["user_id"],
                },
            }
        )

        payment_url = ""

        return PaymentResult(
            provider="razorpay",
            payment_id=order["id"],
            payment_url=payment_url,
            raw=order,
        )

    async def verify_webhook(
        self,
        headers: dict[str, str],
        body: bytes,
    ) -> WebhookResult:

        signature = headers.get("x-razorpay-signature")

        if not signature:
            raise ValueError("Missing Razorpay signature")

        expected = hmac.new(
            settings.RAZORPAY_WEBHOOK_SECRET.encode(),
            body,
            hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(expected, signature):
            raise ValueError("Invalid webhook signature")

        payload = json.loads(body.decode())

        entity = payload["payload"]["payment"]["entity"]

        return WebhookResult(
            provider="razorpay",
            order_id=entity["order_id"],
            payment_id=entity["id"],
            status=entity["status"].upper(),
            amount=Decimal(entity["amount"]) / Decimal("100"),
            currency=entity["currency"],
            raw=payload,
        )

    async def refund(
        self,
        payment_id: str,
        amount: Decimal,
        reason: str | None = None,
    ) -> RefundResult:

        refund = self.client.payment.refund(
            payment_id,
            {
                "amount": int(amount * 100),
                "notes": {
                    "reason": reason or "",
                },
            },
        )

        return RefundResult(
            provider="razorpay",
            refund_id=refund["id"],
            payment_id=payment_id,
            amount=amount,
            status=refund["status"],
            raw=refund,
        )

    async def fetch_settlements(
        self,
    ) -> list[SettlementResult]:

        settlements = self.client.settlement.all()

        results = []

        for s in settlements["items"]:

            results.append(
                SettlementResult(
                    provider="razorpay",
                    settlement_reference=s["id"],
                    amount=Decimal(s["amount"]) / Decimal("100"),
                    currency="INR",
                    status=s["status"],
                    settlement_date=s["created_at"],
                    raw=s,
                )
            )

        return results

    async def health_check(self) -> bool:

        try:
            self.client.order.all({"count": 1})
            return True
        except Exception:
            return False