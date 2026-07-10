"""
India Post (Speed Post / Dak) carrier adapter.

India Post is typically used as the fallback carrier for remote / low-density
pincodes where private couriers like Delhivery lack coverage. Its public API
surface is more limited, so estimates lean on static heuristics where a live
rate-card endpoint isn't available.
"""
from datetime import datetime, timezone

import httpx

from app.adapters.base import (
    BaseCarrierAdapter,
    CarrierAPIError,
    ServiceabilityResult,
    ShipmentBookingResult,
    TrackingUpdate,
)
from app.config import get_settings

settings = get_settings()

_STATUS_MAP = {
    "booked": "created",
    "collected": "picked_up",
    "in transit": "in_transit",
    "out for delivery": "out_for_delivery",
    "delivered": "delivered",
    "returned": "return_to_origin",
    "undelivered": "failed",
}


class IndiaPostAdapter(BaseCarrierAdapter):
    code = "india_post"

    def __init__(self, client: httpx.AsyncClient | None = None):
        self._client = client or httpx.AsyncClient(
            base_url=settings.india_post_api_base,
            headers={"x-api-key": settings.india_post_api_key},
            timeout=15.0,
        )

    async def check_serviceability(
        self, origin_pincode: str, destination_pincode: str, weight_kg: float
    ) -> ServiceabilityResult:
        try:
            resp = await self._client.get(
                "/v1/pincode/serviceability",
                params={"origin": origin_pincode, "destination": destination_pincode},
            )
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPError as exc:
            raise CarrierAPIError(f"India Post serviceability check failed: {exc}") from exc

        # India Post services virtually every pincode in India (universal
        # service obligation), so we treat an explicit "false" as the only
        # non-serviceable case, defaulting to True otherwise.
        serviceable = data.get("serviceable", True)
        estimated_cost = 20 + (weight_kg * 12)
        estimated_hours = 96.0  # slower than private couriers on average
        return ServiceabilityResult(serviceable, estimated_cost, estimated_hours)

    async def create_shipment(
        self,
        order_id: str,
        origin_pincode: str,
        destination_pincode: str,
        weight_kg: float,
        cod_amount: float,
    ) -> ShipmentBookingResult:
        payload = {
            "reference_id": order_id,
            "origin_pincode": origin_pincode,
            "destination_pincode": destination_pincode,
            "weight_grams": int(weight_kg * 1000),
            "cod_amount": cod_amount,
        }
        try:
            resp = await self._client.post("/v1/speedpost/book", json=payload)
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPError as exc:
            raise CarrierAPIError(f"India Post shipment creation failed: {exc}") from exc

        consignment_no = data.get("consignment_number")
        if not consignment_no:
            raise CarrierAPIError(f"India Post did not return a consignment number: {data}")

        return ShipmentBookingResult(carrier_awb=consignment_no, label_url=data.get("label_url"), raw_response=data)

    async def create_reverse_pickup(
        self, awb: str, pickup_pincode: str, reason: str, weight_kg: float
    ) -> ShipmentBookingResult:
        payload = {
            "original_consignment_number": awb,
            "pickup_pincode": pickup_pincode,
            "reason": reason,
            "weight_grams": int(weight_kg * 1000),
        }
        try:
            resp = await self._client.post("/v1/speedpost/reverse-pickup", json=payload)
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPError as exc:
            raise CarrierAPIError(f"India Post reverse pickup failed: {exc}") from exc

        reverse_id = data.get("consignment_number", awb)
        return ShipmentBookingResult(carrier_awb=reverse_id, label_url=None, raw_response=data)

    async def fetch_tracking(self, awb: str) -> list[TrackingUpdate]:
        try:
            resp = await self._client.get(f"/v1/speedpost/track/{awb}")
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPError as exc:
            raise CarrierAPIError(f"India Post tracking fetch failed: {exc}") from exc

        checkpoints = data.get("checkpoints", [])
        updates = []
        for cp in checkpoints:
            event_time_str = cp.get("timestamp")
            try:
                event_time = datetime.fromisoformat(event_time_str) if event_time_str else datetime.now(timezone.utc)
            except ValueError:
                event_time = datetime.now(timezone.utc)

            status_label = (cp.get("status") or "").lower()
            updates.append(
                TrackingUpdate(
                    status=_STATUS_MAP.get(status_label, "in_transit"),
                    location=cp.get("office"),
                    remarks=cp.get("description"),
                    event_time=event_time,
                    raw_payload=cp,
                )
            )
        return updates

    async def aclose(self) -> None:
        await self._client.aclose()
