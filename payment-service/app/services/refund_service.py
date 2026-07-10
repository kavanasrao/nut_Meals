"""
Refund Service - Handles full and partial refunds.
"""

from __future__ import annotations

import logging
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.events.events import EventType
from app.events.publisher import EventPublisher
from app.models.payment import Payment, PaymentStatus
from app.models.refund import Refund, RefundStatus
from app.providers.factory import get_payment_provider
from app.schemas.refund import RefundCreate

logger = logging.getLogger(__name__)


class RefundService:
    """
    Business logic for payment refunds.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.provider = get_payment_provider()

    async def create_refund(self, data: RefundCreate) -> Refund:
        """
        Create a refund for a successful payment.
        Supports partial refunds.
        """

        payment = await self.db.get(Payment, data.payment_id)

        if payment is None:
            raise ValueError("Payment not found")

        if payment.status not in (
            PaymentStatus.SUCCESS,
            PaymentStatus.REFUNDED,
        ):
            raise ValueError(
                f"Cannot refund payment in status '{payment.status.value}'"
            )

        # Calculate existing successful refunds
        result = await self.db.execute(
            select(Refund).where(
                Refund.payment_id == payment.id,
                Refund.status == RefundStatus.SUCCESS,
            )
        )

        previous_refunds = result.scalars().all()

        refunded_amount = sum(
            (refund.amount for refund in previous_refunds),
            Decimal("0.00"),
        )

        if refunded_amount + data.amount > payment.amount:
            raise ValueError("Refund amount exceeds payment amount.")

        # Call payment gateway
        provider_result = await self.provider.refund(
            payment_id=payment.provider_payment_id,
            amount=data.amount,
            reason=data.reason,
        )

        refund = Refund(
            payment_id=payment.id,
            amount=data.amount,
            reason=data.reason,
            provider_refund_id=provider_result.refund_id,
            initiated_by=data.initiated_by,
            status=RefundStatus.SUCCESS,
        )

        self.db.add(refund)

        total_refunded = refunded_amount + data.amount

        # Update payment status
        if total_refunded == payment.amount:
            payment.status = PaymentStatus.REFUNDED

        await self.db.commit()

        await self.db.refresh(refund)

        await EventPublisher.publish(
            EventType.REFUND_SUCCESS,
            {
                "refund_id": str(refund.id),
                "payment_id": str(payment.id),
                "order_id": payment.order_id,
                "amount": str(refund.amount),
            },
        )

        logger.info(
            "Refund %s processed successfully.",
            refund.id,
        )

        return refund

    async def get_refund(
        self,
        refund_id: UUID | str,
    ) -> Refund | None:
        """
        Fetch refund by ID.
        """

        return await self.db.get(
            Refund,
            refund_id,
        )

    async def get_payment_refunds(
        self,
        payment_id: UUID | str,
    ) -> list[Refund]:
        """
        Get all refunds for a payment.
        """

        result = await self.db.execute(
            select(Refund).where(
                Refund.payment_id == payment_id
            )
        )

        return list(result.scalars().all())