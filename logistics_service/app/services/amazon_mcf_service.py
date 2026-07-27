"""
Business service for Amazon Multi-Channel Fulfillment (MCF).
"""

from __future__ import annotations

from app.adapters.amazon_mcf import AmazonMCFAdapter
from app.schemas.amazon_mcf import (
    FulfillmentOrderCreate,
)


class AmazonMCFService:
    def __init__(self) -> None:
        self.adapter = AmazonMCFAdapter()

    async def create_order(
        self,
        order: FulfillmentOrderCreate,
    ) -> dict:
        """
        Create a fulfillment order in Amazon MCF.
        """
        payload = order.model_dump(
            mode="json",
            exclude_none=True,
        )

        return await self.adapter.create_fulfillment_order(
            payload
        )

    async def get_order(
        self,
        order_id: str,
    ) -> dict:
        """
        Retrieve a fulfillment order.
        """
        return await self.adapter.get_fulfillment_order(
            order_id
        )

    async def list_orders(
        self,
    ) -> list[dict]:
        """
        List all fulfillment orders.
        """
        return await self.adapter.list_fulfillment_orders()

    async def cancel_order(
        self,
        order_id: str,
    ) -> dict:
        """
        Cancel a fulfillment order.
        """
        return await self.adapter.cancel_fulfillment_order(
            order_id
        )

    async def get_inventory(
        self,
    ) -> list[dict]:
        """
        Get Amazon fulfillable inventory.
        """
        return await self.adapter.get_inventory()

    async def get_tracking(
        self,
        order_id: str,
    ) -> dict:
        """
        Retrieve shipment tracking details.
        """
        return await self.adapter.get_tracking(
            order_id
        )