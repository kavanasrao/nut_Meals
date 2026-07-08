"""Event definitions for the Payment Service."""
from __future__ import annotations
from enum import Enum


class EventType(str, Enum):
    PAYMENT_SUCCESS = "PAYMENT_SUCCESS"
    PAYMENT_FAILED = "PAYMENT_FAILED"
    ORDER_CREATED = "ORDER_CREATED"
