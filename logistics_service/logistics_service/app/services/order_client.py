"""Thin client for pushing shipment status updates to the Orders service."""
import logging

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


async def sync_order_shipment_status(order_id: str, status: str, carrier_awb: str | None) -> bool:
    """Push a shipment status update to Orders. Returns True on success."""
    payload = {"status": status, "carrier_awb": carrier_awb}
    try:
        async with httpx.AsyncClient(base_url=settings.orders_service_url, timeout=5.0) as client:
            resp = await client.patch(f"/v1/orders/{order_id}/shipment-status", json=payload)
            resp.raise_for_status()
        return True
    except httpx.HTTPError as exc:
        logger.error("Failed to sync order %s shipment status: %s", order_id, exc)
        return False


async def notify_inventory_of_return(order_id: str, sku_items: list[dict]) -> bool:
    """Notify the Inventory service to restock items from a completed return."""
    try:
        async with httpx.AsyncClient(base_url=settings.inventory_service_url, timeout=5.0) as client:
            resp = await client.post(
                "/v1/inventory/restock", json={"order_id": order_id, "items": sku_items}
            )
            resp.raise_for_status()
        return True
    except httpx.HTTPError as exc:
        logger.error("Failed to notify inventory for return on order %s: %s", order_id, exc)
        return False
