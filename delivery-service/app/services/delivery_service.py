"""Delivery Service — business logic layer.

Handles:
  - Delivery options query with availability filtering and ETA calculation
  - Redis caching for options (5-min TTL)
  - Order event consumption → delivery assignment
"""
from __future__ import annotations

import json
import logging
import math
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.redis import get_redis
from app.models.delivery import DeliveryAssignment, DeliveryStatus
from app.schemas.delivery import DeliveryOption, DeliveryOptionsResponse

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Geo helpers
# ---------------------------------------------------------------------------

def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return great-circle distance in kilometres between two coordinates."""
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lam = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lam / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _parse_location(location: str) -> tuple[float, float] | None:
    """
    Parse a location string of the form 'lat,lon' (e.g. '12.9716,77.5946').
    Returns (lat, lon) or None if parsing fails.
    """
    try:
        parts = location.split(",")
        if len(parts) == 2:
            return float(parts[0].strip()), float(parts[1].strip())
    except ValueError:
        pass
    return None


def _is_service_open() -> bool:
    """Return True if current UTC time is within operating hours."""
    now_hour = datetime.now(timezone.utc).hour
    return settings.SERVICE_START_HOUR <= now_hour < settings.SERVICE_END_HOUR


# ---------------------------------------------------------------------------
# Delivery Service
# ---------------------------------------------------------------------------

class DeliveryService:
    """All delivery-related business operations."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ------------------------------------------------------------------
    # Delivery options
    # ------------------------------------------------------------------

    async def get_delivery_options(self, location: str) -> DeliveryOptionsResponse:
        """
        Return available delivery methods for the given location.
        Results are cached in Redis for DELIVERY_OPTIONS_CACHE_TTL seconds.

        Location format: "lat,lon" (e.g. "12.9716,77.5946")
        """
        cache_key = f"delivery_options:{location}"
        redis = await get_redis()

        # Cache hit
        cached = await redis.get(cache_key)
        if cached:
            data = json.loads(cached)
            return DeliveryOptionsResponse(**data)

        # Build options
        options = self._build_options(location)
        response = DeliveryOptionsResponse(options=options, location=location)

        # Cache for TTL
        await redis.setex(
            cache_key,
            settings.DELIVERY_OPTIONS_CACHE_TTL,
            response.model_dump_json(),
        )

        return response

    def _build_options(self, location: str) -> list[DeliveryOption]:
        coords = _parse_location(location)
        service_open = _is_service_open()

        options: list[DeliveryOption] = []

        # ── Pickup ──────────────────────────────────────────────────────
        if not service_open:
            options.append(DeliveryOption(
                type="pickup",
                available=False,
                eta="N/A",
                eta_minutes=0,
                reason_unavailable=(
                    f"Kitchen is closed. Opens at {settings.SERVICE_START_HOUR:02d}:00 UTC."
                ),
            ))
        else:
            options.append(DeliveryOption(
                type="pickup",
                available=True,
                eta=f"{settings.PICKUP_BASE_ETA_MINUTES} mins",
                eta_minutes=settings.PICKUP_BASE_ETA_MINUTES,
            ))

        # ── Home delivery ────────────────────────────────────────────────
        if not service_open:
            options.append(DeliveryOption(
                type="home_delivery",
                available=False,
                eta="N/A",
                eta_minutes=0,
                reason_unavailable="Service is closed.",
            ))
        elif coords is None:
            options.append(DeliveryOption(
                type="home_delivery",
                available=False,
                eta="N/A",
                eta_minutes=0,
                reason_unavailable="Invalid location format. Use 'lat,lon'.",
            ))
        else:
            user_lat, user_lon = coords
            distance_km = _haversine_km(
                settings.RESTAURANT_LAT, settings.RESTAURANT_LON,
                user_lat, user_lon,
            )
            if distance_km > settings.HOME_DELIVERY_RADIUS_KM:
                options.append(DeliveryOption(
                    type="home_delivery",
                    available=False,
                    eta="N/A",
                    eta_minutes=0,
                    reason_unavailable=(
                        f"Your location is {distance_km:.1f} km away. "
                        f"Home delivery covers up to {settings.HOME_DELIVERY_RADIUS_KM} km."
                    ),
                ))
            else:
                # ETA = base time + 2 minutes per km
                eta_minutes = settings.HOME_DELIVERY_BASE_ETA_MINUTES + int(distance_km * 2)
                options.append(DeliveryOption(
                    type="home_delivery",
                    available=True,
                    eta=f"{eta_minutes} mins",
                    eta_minutes=eta_minutes,
                ))

        return options

    # ------------------------------------------------------------------
    # Delivery assignment (triggered by ORDER_CREATED event)
    # ------------------------------------------------------------------

    async def assign_delivery(self, order_data: dict[str, Any]) -> DeliveryAssignment:
        """Persist a delivery assignment for an incoming order event."""
        import uuid

        coords = None
        address = order_data.get("delivery_address") or {}
        location_str = address.get("location", "")
        if location_str:
            coords = _parse_location(location_str)

        # Stub rider assignment — replace with real dispatch logic
        rider_id = "auto-assigned"
        rider_name = "Nutmeals Rider"
        rider_phone = "+919999999999"

        delivery_type = order_data.get("delivery_type", "home_delivery")
        eta_minutes = (
            settings.PICKUP_BASE_ETA_MINUTES
            if delivery_type == "pickup"
            else settings.HOME_DELIVERY_BASE_ETA_MINUTES
        )

        assignment = DeliveryAssignment(
            id=uuid.uuid4(),
            order_id=order_data["order_id"],
            user_id=order_data["user_id"],
            delivery_type=delivery_type,
            rider_id=rider_id,
            rider_name=rider_name,
            rider_phone=rider_phone,
            status=DeliveryStatus.ASSIGNED,
            eta_minutes=eta_minutes,
            delivery_address=address or None,
            user_lat=coords[0] if coords else None,
            user_lon=coords[1] if coords else None,
        )
        self.db.add(assignment)
        await self.db.commit()
        await self.db.refresh(assignment)
        logger.info("Delivery assigned for order %s", order_data["order_id"])
        return assignment
