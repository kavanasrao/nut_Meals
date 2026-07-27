"""
Amazon Multi-Channel Fulfillment (MCF) adapter.

Handles communication with the Amazon Selling Partner API.
"""

from __future__ import annotations

from typing import Any

import httpx

from app.config import get_settings

settings = get_settings()


class AmazonMCFAdapter:
    BASE_URL = settings.AMAZON_MCF_BASE_URL

    def __init__(self) -> None:
        self.headers = {
            "Authorization": f"Bearer {settings.AMAZON_MCF_ACCESS_TOKEN}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def create_fulfillment_order(
        self,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Create a fulfillment order.
        """
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{self.BASE_URL}/orders",
                headers=self.headers,
                json=payload,
            )

            response.raise_for_status()
            return response.json()

    async def get_fulfillment_order(
        self,
        order_id: str,
    ) -> dict[str, Any]:
        """
        Retrieve a fulfillment order.
        """
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                f"{self.BASE_URL}/orders/{order_id}",
                headers=self.headers,
            )

            response.raise_for_status()
            return response.json()

    async def cancel_fulfillment_order(
        self,
        order_id: str,
    ) -> dict[str, Any]:
        """
        Cancel a fulfillment order.
        """
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.delete(
                f"{self.BASE_URL}/orders/{order_id}",
                headers=self.headers,
            )

            response.raise_for_status()
            return response.json()

    async def list_fulfillment_orders(
        self,
    ) -> list[dict[str, Any]]:
        """
        List fulfillment orders.
        """
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                f"{self.BASE_URL}/orders",
                headers=self.headers,
            )

            response.raise_for_status()
            return response.json()

    async def get_inventory(
        self,
    ) -> list[dict[str, Any]]:
        """
        Get Amazon MCF inventory.
        """
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                f"{self.BASE_URL}/inventory",
                headers=self.headers,
            )

            response.raise_for_status()
            return response.json()

    async def get_tracking(
        self,
        order_id: str,
    ) -> dict[str, Any]:
        """
        Get shipment tracking.
        """
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                f"{self.BASE_URL}/orders/{order_id}/tracking",
                headers=self.headers,
            )

            response.raise_for_status()
            return response.json()