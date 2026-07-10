"""
Event definitions for the Orders Service.
"""

from __future__ import annotations

from enum import Enum


class EventType(str, Enum):

    # ==========================================================
    # Orders
    # ==========================================================

    ORDER_CREATED = "ORDER_CREATED"
    ORDER_CONFIRMED = "ORDER_CONFIRMED"
    ORDER_CANCELLED = "ORDER_CANCELLED"

    # ==========================================================
    # Returns
    # ==========================================================

    RETURN_CREATED = "RETURN_CREATED"

    RETURN_APPROVED = "RETURN_APPROVED"

    RETURN_REJECTED = "RETURN_REJECTED"

    RETURN_COMPLETED = "RETURN_COMPLETED"

    RETURN_INSPECTION_REQUIRED = "RETURN_INSPECTION_REQUIRED"

    # ==========================================================
    # Logistics
    # ==========================================================

    PICKUP_REQUESTED = "PICKUP_REQUESTED"

    PICKUP_COMPLETED = "PICKUP_COMPLETED"

    # ==========================================================
    # Payments
    # ==========================================================

    REFUND_REQUESTED = "REFUND_REQUESTED"

    REFUND_COMPLETED = "REFUND_COMPLETED"

    # ==========================================================
    # Inventory
    # ==========================================================

    STOCK_RETURNED = "STOCK_RETURNED"

    STOCK_INSPECTION_REQUIRED = "STOCK_INSPECTION_REQUIRED"

    STOCK_REJECTED = "STOCK_REJECTED"

    # ==========================================================
    # Notifications
    # ==========================================================

    CUSTOMER_NOTIFICATION = "CUSTOMER_NOTIFICATION"

    EMAIL_NOTIFICATION = "EMAIL_NOTIFICATION"

    SMS_NOTIFICATION = "SMS_NOTIFICATION"