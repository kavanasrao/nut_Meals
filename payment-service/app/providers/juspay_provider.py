"""Juspay payment provider implementation.

Docs: https://developer.juspay.in/
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
from typing import Any

import httpx

from app.core.config import settings
from app.providers.base import PaymentProvider, PaymentResult, WebhookResult

logger = logging.getLogger(__name__)


class JuspayProvider(PaymentProvider):
    """Production-ready Juspay adapter."""

    def get_name(self) -> str:
        return "juspay"

    # ── Create payment ───────────────────────────────────────────────────

    async def create_payment(self, data: dict[str, Any]) -> PaymentResult:
        if not (settings.JUSPAY_API_KEY and settings.JUSPAY_MERCHANT_ID):
            # Sandbox / stub mode — still returns a usable shape
            logger.warning("Juspay credentials not set; returning stub payment URL")
            return PaymentResult(
                provider=self.get_name(),
                payment_id=f"stub_{data['order_id']}",
                payment_url=f"{settings.JUSPAY_BASE_URL}/checkout/{data['order_id']}",
                raw={},
            )

        payload = {
            "order_id": data["order_id"],
            "amount": data["amount"],
            "currency": "INR",
            "customer_id": data["user_id"],
            "customer_email": data.get("email", ""),
            "customer_phone": data.get("phone", ""),
            "return_url": data.get("return_url", "https://nutmeals.in/payment/return"),
            "udf1": data["order_id"],  # echo back for webhook correlation
        }

        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(
                f"{settings.JUSPAY_BASE_URL}/session",
                json=payload,
                auth=(settings.JUSPAY_API_KEY, ""),
                headers={"x-merchantid": settings.JUSPAY_MERCHANT_ID},
            )
            response.raise_for_status()
            raw = response.json()

        payment_url = (
            raw.get("payment_links", {}).get("web")
            or raw.get("redirect_url")
            or f"{settings.JUSPAY_BASE_URL}/checkout/{data['order_id']}"
        )

        return PaymentResult(
            provider=self.get_name(),
            payment_id=raw.get("id", data["order_id"]),
            payment_url=payment_url,
            raw=raw,
        )

    # ── Verify webhook ───────────────────────────────────────────────────

    async def verify_webhook(
        self, headers: dict[str, str], body: bytes
    ) -> WebhookResult:
        """
        Juspay signs webhook payloads with HMAC-SHA256 using the webhook secret.
        Header: x-jp-signature
        """
        signature = headers.get("x-jp-signature", "")
        if not signature:
            raise ValueError("Missing x-jp-signature header in Juspay webhook")

        if settings.JUSPAY_WEBHOOK_SECRET:
            expected = hmac.new(
                settings.JUSPAY_WEBHOOK_SECRET.encode(),
                body,
                hashlib.sha256,
            ).hexdigest()
            if not hmac.compare_digest(signature, expected):
                raise ValueError("Juspay webhook signature verification failed")

        raw: dict[str, Any] = json.loads(body)

        # Juspay webhook event schema
        content = raw.get("content", {})
        order = content.get("order", {})
        payment = content.get("payment", {})

        # Map Juspay status → normalised status
        juspay_status = order.get("status", "").upper()
        status_map = {
            "CHARGED": "SUCCESS",
            "AUTHORIZATION_FAILED": "FAILED",
            "AUTHENTICATION_FAILED": "FAILED",
            "COD_INITIATED": "PENDING",
            "PENDING_VBV": "PENDING",
        }
        normalised_status = status_map.get(juspay_status, "PENDING")

        return WebhookResult(
            provider=self.get_name(),
            order_id=order.get("udf1") or order.get("order_id", ""),
            payment_id=payment.get("txn_id") or order.get("id", ""),
            status=normalised_status,
            amount=str(order.get("amount", "0")),
            raw=raw,
        )
