"""
Domain events for the Payment Service.
"""

from __future__ import annotations

from enum import Enum


class EventType(str, Enum):
    """
    Events emitted by the Payment Service.
    """

    # -------------------------------------------------
    # Payment Lifecycle
    # -------------------------------------------------

    PAYMENT_CREATED = "PAYMENT_CREATED"

    PAYMENT_PENDING = "PAYMENT_PENDING"

    PAYMENT_SUCCESS = "PAYMENT_SUCCESS"

    PAYMENT_FAILED = "PAYMENT_FAILED"

    PAYMENT_CANCELLED = "PAYMENT_CANCELLED"

    # -------------------------------------------------
    # Refunds
    # -------------------------------------------------

    REFUND_INITIATED = "REFUND_INITIATED"

    REFUND_SUCCESS = "REFUND_SUCCESS"

    REFUND_FAILED = "REFUND_FAILED"

    # -------------------------------------------------
    # Settlements
    # -------------------------------------------------

    SETTLEMENT_IMPORTED = "SETTLEMENT_IMPORTED"

    SETTLEMENT_RECONCILED = "SETTLEMENT_RECONCILED"

    SETTLEMENT_MISMATCH = "SETTLEMENT_MISMATCH"

    # -------------------------------------------------
    # Orders
    # -------------------------------------------------

    ORDER_CREATED = "ORDER_CREATED"

    ORDER_CONFIRMED = "ORDER_CONFIRMED"

    # -------------------------------------------------
    # Audit
    # -------------------------------------------------

    WEBHOOK_RECEIVED = "WEBHOOK_RECEIVED"

    WEBHOOK_VERIFIED = "WEBHOOK_VERIFIED"
