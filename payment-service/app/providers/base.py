"""
Abstract base class for all payment providers.

Every payment gateway (Razorpay, Juspay, Stripe, Kotak, Cashfree, etc.)
must inherit from PaymentProvider and implement all abstract methods.

Business logic MUST NEVER import a concrete provider directly.
Always use the provider factory.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass
from decimal import Decimal
from typing import Any


# ============================================================================
# Payment Result
# ============================================================================

@dataclass(slots=True)
class PaymentResult:
    """
    Normalized payment creation response.
    """

    provider: str
    payment_id: str
    payment_url: str
    raw: dict[str, Any]


# ============================================================================
# Refund Result
# ============================================================================

@dataclass(slots=True)
class RefundResult:
    """
    Normalized refund response.
    """

    provider: str
    refund_id: str
    payment_id: str
    amount: Decimal
    status: str
    raw: dict[str, Any]


# ============================================================================
# Webhook Result
# ============================================================================

@dataclass(slots=True)
class WebhookResult:
    """
    Normalized webhook payload.
    """

    provider: str
    order_id: str
    payment_id: str
    status: str
    amount: Decimal
    currency: str
    raw: dict[str, Any]


# ============================================================================
# Settlement Result
# ============================================================================

@dataclass(slots=True)
class SettlementResult:
    """
    Normalized settlement record.
    """

    provider: str
    settlement_reference: str
    amount: Decimal
    currency: str
    status: str
    settlement_date: str
    raw: dict[str, Any]


# ============================================================================
# Payment Provider Interface
# ============================================================================

class PaymentProvider(abc.ABC):
    """
    Base interface implemented by every payment gateway.

    Supported gateways:

    - Razorpay
    - Juspay
    - Kotak
    - Stripe
    - Cashfree

    Business logic interacts only with this interface.
    """

    @abc.abstractmethod
    def get_name(self) -> str:
        """
        Return provider name.

        Example:
            razorpay
            juspay
            kotak
        """
        raise NotImplementedError

    # ----------------------------------------------------------------------
    # Payment Creation
    # ----------------------------------------------------------------------

    @abc.abstractmethod
    async def create_payment(
        self,
        data: dict[str, Any],
    ) -> PaymentResult:
        """
        Create a payment session.

        Expected keys:

        order_id
        amount
        user_id
        email
        phone
        return_url
        """
        raise NotImplementedError

    # ----------------------------------------------------------------------
    # Webhook Verification
    # ----------------------------------------------------------------------

    @abc.abstractmethod
    async def verify_webhook(
        self,
        headers: dict[str, str],
        body: bytes,
    ) -> WebhookResult:
        """
        Verify webhook signature.

        Raises:

            ValueError

        if signature verification fails.
        """
        raise NotImplementedError

    # ----------------------------------------------------------------------
    # Refund
    # ----------------------------------------------------------------------

    @abc.abstractmethod
    async def refund(
        self,
        payment_id: str,
        amount: Decimal,
        reason: str | None = None,
    ) -> RefundResult:
        """
        Initiate a full or partial refund.
        """
        raise NotImplementedError

    # ----------------------------------------------------------------------
    # Settlement
    # ----------------------------------------------------------------------

    @abc.abstractmethod
    async def fetch_settlements(
        self,
    ) -> list[SettlementResult]:
        """
        Fetch settlement report from gateway.
        """
        raise NotImplementedError

    # ----------------------------------------------------------------------
    # Health Check
    # ----------------------------------------------------------------------

    @abc.abstractmethod
    async def health_check(self) -> bool:
        """
        Check whether the payment gateway is reachable.

        Returns:
            True if healthy
            False otherwise
        """
        raise NotImplementedError