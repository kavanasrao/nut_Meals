"""
Standardized adapter interface that all carrier integrations must implement.

This decouples the rest of the Logistics Service (rules engine, API routes,
Celery tasks) from any single carrier's API shape. Adding a new carrier means
writing one adapter class and registering it in `app.adapters.registry`.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


class CarrierAPIError(Exception):
    """Raised when a carrier API call fails (network, auth, or business error)."""


@dataclass
class ServiceabilityResult:
    serviceable: bool
    estimated_cost: float
    estimated_hours: float


@dataclass
class ShipmentBookingResult:
    carrier_awb: str
    label_url: str | None
    raw_response: dict


@dataclass
class TrackingUpdate:
    status: str  # maps to ShipmentStatus values
    location: str | None
    remarks: str | None
    event_time: datetime
    raw_payload: dict


class BaseCarrierAdapter(ABC):
    """Every carrier integration implements this contract."""

    code: str  # matches CarrierCode value

    @abstractmethod
    async def check_serviceability(
        self, origin_pincode: str, destination_pincode: str, weight_kg: float
    ) -> ServiceabilityResult:
        """Check whether the carrier services this origin/destination pair."""

    @abstractmethod
    async def create_shipment(
        self,
        order_id: str,
        origin_pincode: str,
        destination_pincode: str,
        weight_kg: float,
        cod_amount: float,
    ) -> ShipmentBookingResult:
        """Book a forward shipment with the carrier, returning an AWB/tracking id."""

    @abstractmethod
    async def create_reverse_pickup(
        self, awb: str, pickup_pincode: str, reason: str, weight_kg: float
    ) -> ShipmentBookingResult:
        """Schedule a reverse pickup (return) for an existing shipment."""

    @abstractmethod
    async def fetch_tracking(self, awb: str) -> list[TrackingUpdate]:
        """Fetch the latest tracking checkpoints for a shipment AWB."""
