"""
Business logic for Returns Management.
"""

from __future__ import annotations

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


from app.models.return_request import (
    ReturnRequest,
    ReturnStatus,
    ReturnResolution,
    ReturnTier,
)

from app.models.return_item import ReturnItem

from app.schemas.returns import (
    ReturnCreate,
)

from app.events.publisher import EventPublisher
from app.events.events import EventType

logger = logging.getLogger(__name__)


class ReturnService:

    def __init__(self, db: AsyncSession):

        self.db = db

    # ==========================================================
    # CREATE RETURN
    # ==========================================================

    async def create_return(
        self,
        data: ReturnCreate,
    ) -> ReturnRequest:

        request = ReturnRequest(

            id=uuid.uuid4(),

            order_id=data.order_id,

            user_id=data.user_id,

            reason=data.reason,

            tier=data.tier,

            status=ReturnStatus.REQUESTED,
        )

        self.db.add(request)

        await self.db.flush()

        # Save all return items
        for item in data.items:

            return_item = ReturnItem(

                return_request_id=request.id,

                order_item_id=item.order_item_id,

                product_id=item.product_id,

                product_name=item.product_name,

                sku=item.sku,

                quantity=item.quantity,

                unit_price=item.unit_price,

                refund_amount=item.refund_amount,
            )

            self.db.add(return_item)

        # ------------------------------------------------------
        # Tier Logic
        # ------------------------------------------------------

        if request.tier == ReturnTier.A:

            request.status = ReturnStatus.APPROVED

            request.resolution = ReturnResolution.REFUND

            await EventPublisher.publish(

                EventType.RETURN_APPROVED,

                {
                    "return_id": str(request.id),
                    "order_id": request.order_id,
                    "resolution": "refund",
                },
            )

            await EventPublisher.publish(

                EventType.REFUND_REQUESTED,

                {
                    "return_id": str(request.id),
                },
            )

        elif request.tier == ReturnTier.B:

            request.status = ReturnStatus.INSPECTION_PENDING

            await EventPublisher.publish(

                EventType.RETURN_INSPECTION_REQUIRED,

                {
                    "return_id": str(request.id),
                },
            )

            await EventPublisher.publish(

                EventType.PICKUP_REQUESTED,

                {
                    "return_id": str(request.id),
                },
            )

        else:

            request.status = ReturnStatus.REJECTED

            request.resolution = ReturnResolution.REJECT

            await EventPublisher.publish(

                EventType.RETURN_REJECTED,

                {
                    "return_id": str(request.id),
                },
            )

        await self.db.commit()

        await self.db.refresh(request)

        logger.info(

            "Return %s created.",

            request.id,
        )

        return request

    # ==========================================================
    # APPROVE RETURN
    # ==========================================================

    async def approve_return(
        self,
        request: ReturnRequest,
    ):

        request.status = ReturnStatus.APPROVED

        request.resolution = ReturnResolution.REFUND

        await self.db.commit()

        await EventPublisher.publish(

            EventType.RETURN_APPROVED,

            {
                "return_id": str(request.id),
            },
        )

        return request

    # ==========================================================
    # REJECT RETURN
    # ==========================================================

    async def reject_return(
        self,
        request: ReturnRequest,
    ):

        request.status = ReturnStatus.REJECTED

        request.resolution = ReturnResolution.REJECT

        await self.db.commit()

        await EventPublisher.publish(

            EventType.RETURN_REJECTED,

            {
                "return_id": str(request.id),
            },
        )

        return request

    # ==========================================================
    # COMPLETE RETURN
    # ==========================================================

    async def complete_return(
        self,
        request: ReturnRequest,
    ):

        request.status = ReturnStatus.COMPLETED

        await self.db.commit()

        await EventPublisher.publish(

            EventType.RETURN_COMPLETED,

            {
                "return_id": str(request.id),
            },
        )

        return request
    
    # ==========================================================
    # GET RETURN
    # ==========================================================

    async def get_return(self, return_id,) -> ReturnRequest | None:

        result = await self.db.execute(
            select(ReturnRequest).where(
                ReturnRequest.id == return_id
            )
        )

        return result.scalar_one_or_none()