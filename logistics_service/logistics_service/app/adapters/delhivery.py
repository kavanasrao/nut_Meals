"""
Delhivery carrier adapter.

Wraps Delhivery's REST API behind the standardized BaseCarrierAdapter
interface. Network calls use httpx.AsyncClient; all errors are normalized
to CarrierAPIError so the rules engine / fallback logic can treat every
carrier uniformly.
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

# Maps Delhivery's status vocabulary to our internal ShipmentStatus values.
_STATUS_MAP = {
    "Manifested": "created",
    "Pickup Scheduled": "created",
    "Picked Up": "picked_up",
    "In Transit": "in_transit",
    "Out for Delivery": "out_for_delivery",
    "Delivered": "delivered",
    "RTO": "return_to_origin",
    "Undelivered": "failed",
}


class DelhiveryAdapter(BaseCarrierAdapter):
    code = "delhivery"

    def __init__(self, client: httpx.AsyncClient | None = None):
        self._client = client or httpx.AsyncClient(
            base_url=settings.delhivery_api_base,
            headers={"Authorization": f"Token {settings.delhivery_api_token}"},
            timeout=10.0,
        )

    async def check_serviceability(
        self, origin_pincode: str, destination_pincode: str, weight_kg: float
    ) -> ServiceabilityResult:
        try:
            resp = await self._client.get(
                "/c/api/pin-codes/json/", params={"filter_codes": destination_pincode}
            )
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPError as exc:
            raise CarrierAPIError(f"Delhivery serviceability check failed: {exc}") from exc

        delivery_codes = data.get("delivery_codes", [])
        serviceable = bool(delivery_codes)
        # Cost/time estimates would normally come from a rate-card endpoint;
        # simplified heuristic here based on weight.
        estimated_cost = 30 + (weight_kg * 18)
        estimated_hours = 48.0
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
            "shipments": [
                {
                    "order": order_id,
                    "origin_pin": origin_pincode,
                    "destination_pin": destination_pincode,
                    "weight": weight_kg,
                    "cod_amount": cod_amount,
                    "payment_mode": "COD" if cod_amount > 0 else "Prepaid",
                }
            ]
        }
        try:
            resp = await self._client.post("/api/cmu/create.json", json=payload)
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPError as exc:
            raise CarrierAPIError(f"Delhivery shipment creation failed: {exc}") from exc

        packages = data.get("packages", [])
        if not packages or not packages[0].get("waybill"):
            raise CarrierAPIError(f"Delhivery did not return a waybill: {data}")

        return ShipmentBookingResult(
            carrier_awb=packages[0]["waybill"],
            label_url=packages[0].get("label_url"),
            raw_response=data,
        )

    async def create_reverse_pickup(
        self, awb: str, pickup_pincode: str, reason: str, weight_kg: float
    ) -> ShipmentBookingResult:
        payload = {
            "pickup_location": {"pin": pickup_pincode},
            "reverse_for_awb": awb,
            "reason": reason,
            "weight": weight_kg,
        }
        try:
            resp = await self._client.post("/api/cmu/reverse.json", json=payload)
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPError as exc:
            raise CarrierAPIError(f"Delhivery reverse pickup failed: {exc}") from exc

        reverse_awb = data.get("waybill", awb)
        return ShipmentBookingResult(carrier_awb=reverse_awb, label_url=None, raw_response=data)

    async def fetch_tracking(self, awb: str) -> list[TrackingUpdate]:
        try:
            resp = await self._client.get("/api/v1/packages/json/", params={"waybill": awb})
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPError as exc:
            raise CarrierAPIError(f"Delhivery tracking fetch failed: {exc}") from exc

        shipment_data = (data.get("ShipmentData") or [{}])[0].get("Shipment", {})
        scans = shipment_data.get("Scans", [])

        updates = []
        for scan in scans:
            scan_detail = scan.get("ScanDetail", {})
            status_label = scan_detail.get("Scan", "In Transit")
            event_time_str = scan_detail.get("StatusDateTime")
            try:
                event_time = datetime.fromisoformat(event_time_str) if event_time_str else datetime.now(timezone.utc)
            except ValueError:
                event_time = datetime.now(timezone.utc)

            updates.append(
                TrackingUpdate(
                    status=_STATUS_MAP.get(status_label, "in_transit"),
                    location=scan_detail.get("ScannedLocation"),
                    remarks=scan_detail.get("Instructions"),
                    event_time=event_time,
                    raw_payload=scan,
                )
            )
        return updates

    async def aclose(self) -> None:
        await self._client.aclose()
