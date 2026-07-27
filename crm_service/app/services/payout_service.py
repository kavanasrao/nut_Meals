"""
Affiliate Payout Service.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.affiliate_payout import (
    AffiliatePayout,
    PayoutStatus,
)
from app.schema.affiliate_payout import (
    AffiliatePayoutCreate,
    AffiliatePayoutUpdate,
)


class PayoutService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # =====================================================
    # CREATE
    # =====================================================

    async def create_payout(
        self,
        payload: AffiliatePayoutCreate,
    ) -> AffiliatePayout:

        payout = AffiliatePayout(
            affiliate_id=payload.affiliate_id,
            payout_reference=payload.payout_reference,
            payout_method=payload.payout_method,
            amount=payload.amount,
            currency=payload.currency,
            bank_reference=payload.bank_reference,
            transaction_reference=payload.transaction_reference,
            failure_reason=payload.failure_reason,
            requested_by=payload.requested_by,
        )

        self.db.add(payout)

        await self.db.commit()
        await self.db.refresh(payout)

        return payout

    # =====================================================
    # GET
    # =====================================================

    async def get_payout(
        self,
        payout_id: UUID,
    ) -> AffiliatePayout:

        payout = await self.db.get(
            AffiliatePayout,
            payout_id,
        )

        if payout is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Payout not found.",
            )

        return payout

    # =====================================================
    # LIST
    # =====================================================

    async def list_payouts(
        self,
    ) -> list[AffiliatePayout]:

        result = await self.db.execute(
            select(AffiliatePayout).order_by(
                AffiliatePayout.created_at.desc()
            )
        )

        return list(result.scalars().all())
    
    # =====================================================
    # UPDATE
    # =====================================================

    async def update_payout(
        self,
        payout_id: UUID,
        payload: AffiliatePayoutUpdate,
    ) -> AffiliatePayout:

        payout = await self.get_payout(
            payout_id
        )

        update_data = payload.model_dump(
            exclude_unset=True,
            exclude_none=True,
        )

        for key, value in update_data.items():
            setattr(payout, key, value)

        await self.db.commit()
        await self.db.refresh(payout)

        return payout

    # =====================================================
    # APPROVE
    # =====================================================

    async def approve_payout(
        self,
        payout_id: UUID,
        approved_by: str,
    ) -> AffiliatePayout:

        payout = await self.get_payout(
            payout_id
        )

        payout.status = PayoutStatus.PROCESSING
        payout.approved_by = approved_by

        await self.db.commit()
        await self.db.refresh(payout)

        return payout

    # =====================================================
    # MARK AS PAID
    # =====================================================

    async def mark_as_paid(
        self,
        payout_id: UUID,
        transaction_reference: str | None = None,
    ) -> AffiliatePayout:

        payout = await self.get_payout(
            payout_id
        )

        payout.status = PayoutStatus.PAID

        if transaction_reference:
            payout.transaction_reference = transaction_reference

        await self.db.commit()
        await self.db.refresh(payout)

        return payout
    
    # =====================================================
    # MARK AS FAILED
    # =====================================================

    async def mark_as_failed(
        self,
        payout_id: UUID,
        failure_reason: str,
    ) -> AffiliatePayout:

        payout = await self.get_payout(
            payout_id
        )

        payout.status = PayoutStatus.FAILED
        payout.failure_reason = failure_reason

        await self.db.commit()
        await self.db.refresh(payout)

        return payout

    # =====================================================
    # LIST BY STATUS
    # =====================================================

    async def list_by_status(
        self,
        status: PayoutStatus,
    ) -> list[AffiliatePayout]:

        result = await self.db.execute(
            select(AffiliatePayout)
            .where(
                AffiliatePayout.status == status
            )
            .order_by(
                AffiliatePayout.created_at.desc()
            )
        )

        return list(result.scalars().all())

    # =====================================================
    # LIST BY AFFILIATE
    # =====================================================

    async def list_by_affiliate(
        self,
        affiliate_id: UUID,
    ) -> list[AffiliatePayout]:

        result = await self.db.execute(
            select(AffiliatePayout)
            .where(
                AffiliatePayout.affiliate_id == affiliate_id
            )
            .order_by(
                AffiliatePayout.created_at.desc()
            )
        )

        return list(result.scalars().all())

    # =====================================================
    # DELETE
    # =====================================================

    async def delete_payout(
        self,
        payout_id: UUID,
    ) -> None:

        payout = await self.get_payout(
            payout_id
        )

        await self.db.delete(payout)
        await self.db.commit()

    # =====================================================
    # TOTAL PAID AMOUNT
    # =====================================================

    async def total_paid_amount(
        self,
        affiliate_id: UUID,
    ) -> int:

        result = await self.db.execute(
            select(AffiliatePayout).where(
                AffiliatePayout.affiliate_id == affiliate_id,
                AffiliatePayout.status == PayoutStatus.PAID,
            )
        )

        payouts = result.scalars().all()

        return sum(
            payout.amount
            for payout in payouts
        )