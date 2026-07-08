"""Razorpay payment provider — placeholder implementation.

Activate by:
  1. pip install razorpay
  2. Set PAYMENT_PROVIDER=razorpay and RAZORPAY_KEY_ID / RAZORPAY_KEY_SECRET in .env
  3. Implement the methods below following the Razorpay API docs.
"""
from __future__ import annotations

from typing import Any

from app.providers.base import PaymentProvider, PaymentResult, WebhookResult


class RazorpayProvider(PaymentProvider):
    """Placeholder Razorpay adapter — implement when Razorpay is needed."""

    def get_name(self) -> str:
        return "razorpay"

    async def create_payment(self, data: dict[str, Any]) -> PaymentResult:
        # TODO: implement using razorpay.Client
        # client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        # order = client.order.create({"amount": int(float(data["amount"])*100), "currency": "INR", ...})
        raise NotImplementedError("RazorpayProvider.create_payment is not yet implemented.")

    async def verify_webhook(
        self, headers: dict[str, str], body: bytes
    ) -> WebhookResult:
        # TODO: verify using razorpay.Utility.verify_webhook_signature()
        raise NotImplementedError("RazorpayProvider.verify_webhook is not yet implemented.")
