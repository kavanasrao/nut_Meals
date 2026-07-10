"""Thin async HTTP client for the Inventory Service (separate microservice).

Catalog does not own stock data; it calls Inventory over HTTP for live
availability, and falls back to the last cached value on `Product`/`ProductVariant`
if Inventory is unreachable (graceful degradation).
"""
import logging
from typing import Dict, Optional

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class InventoryClient:
    def __init__(self, base_url: Optional[str] = None, timeout: Optional[float] = None):
        self.base_url = base_url or settings.inventory_service_url
        self.timeout = timeout or settings.inventory_service_timeout_seconds

    async def get_stock_for_skus(self, skus: list[str]) -> Dict[str, dict]:
        """Returns {sku: {"is_in_stock": bool, "quantity_available": int}}.

        On failure, returns an empty dict — callers should fall back to cached
        stock flags rather than fail the whole request.
        """
        if not skus:
            return {}
        try:
            async with httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout) as client:
                resp = await client.post("/internal/stock/batch", json={"skus": skus})
                resp.raise_for_status()
                data = resp.json()
                return {item["sku"]: item for item in data.get("results", [])}
        except (httpx.HTTPError, ValueError) as exc:
            logger.warning("inventory_service_unreachable", extra={"error": str(exc)})
            return {}


def get_inventory_client() -> InventoryClient:
    return InventoryClient()
