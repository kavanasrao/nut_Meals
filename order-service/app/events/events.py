"""Canonical event type definitions shared across all services.

Each service has its own copy — this is intentional in a microservices
architecture to avoid shared library coupling.
"""
from __future__ import annotations

from enum import Enum


class EventType(str, Enum):
    ORDER_CREATED = "ORDER_CREATED"
    ORDER_UPDATED = "ORDER_UPDATED"
    ORDER_CANCELLED = "ORDER_CANCELLED"
    PAYMENT_SUCCESS = "PAYMENT_SUCCESS"
    PAYMENT_FAILED = "PAYMENT_FAILED"
    DELIVERY_ASSIGNED = "DELIVERY_ASSIGNED"
    DELIVERY_COMPLETED = "DELIVERY_COMPLETED"
    DELIVERY_FAILED = "DELIVERY_FAILED"
