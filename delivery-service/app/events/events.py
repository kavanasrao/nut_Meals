"""Event definitions for Delivery Service."""
from __future__ import annotations
from enum import Enum


class EventType(str, Enum):
    ORDER_CREATED = "ORDER_CREATED"
    DELIVERY_ASSIGNED = "DELIVERY_ASSIGNED"
    DELIVERY_COMPLETED = "DELIVERY_COMPLETED"
    DELIVERY_FAILED = "DELIVERY_FAILED"
