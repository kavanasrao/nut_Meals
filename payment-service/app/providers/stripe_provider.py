"""Stripe payment provider — placeholder implementation.

Activate by:
  1. pip install stripe
  2. Set PAYMENT_PROVIDER=stripe and STRIPE_SECRET_KEY / STRIPE_WEBHOOK_SECRET in .env
  3. Implement the methods below following the Stripe API docs.
"""
from __future__ import annotations

import json
import logging
from typing import Any

from app.providers.base import PaymentProvider, PaymentResult, WebhookResult

logger = logging.getLogger(__name__)


class StripeProvider(PaymentProvider):
    """Placeholder Stripe adapter — implement when Stripe is needed."""

    def get_name(self) -> str:
        return "stripe"

    async def create_payment(self, data: dict[str, Any]) -> PaymentResult:
        # TODO: implement using `stripe.PaymentIntent.create()`
        # import stripe
        # stripe.api_key = settings.STRIPE_SECRET_KEY
        # intent = await stripe.PaymentIntent.acreate(amount=..., currency="inr", ...)
        raise NotImplementedError(
            "StripeProvider.create_payment is not yet implemented. "
            "See the docstring for activation steps."
        )

    async def verify_webhook(
        self, headers: dict[str, str], body: bytes
    ) -> WebhookResult:
        # TODO: implement using stripe.Webhook.construct_event()
        # event = stripe.Webhook.construct_event(body, sig_header, settings.STRIPE_WEBHOOK_SECRET)
        raise NotImplementedError("StripeProvider.verify_webhook is not yet implemented.")
