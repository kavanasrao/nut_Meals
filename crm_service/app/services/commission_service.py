"""
Affiliate Commission Service.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.affiliate_commission import (
    AffiliateCommission,
    CommissionStatus,
)
from app.schema.affiliate_commission import (
    AffiliateCommissionCreate,
    AffiliateCommissionUpdate,
)


class CommissionService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # =====================================================
    # CREATE
    # =====================================================

    async def create_commission(
        self,
        payload: AffiliateCommissionCreate,
    ) -> AffiliateCommission:

        commission = AffiliateCommission(
            affiliate_id=payload.affiliate_id,
            referral_id=payload.referral_id,
            order_id=payload.order_id,
            sales_amount=payload.sales_amount,
            commission_rate=payload.commission_rate,
            commission_amount=payload.commission_amount,
            currency=payload.currency,
            remarks=payload.remarks,
            created_by=payload.created_by,
        )

        self.db.add(commission)

        await self.db.commit()
        await self.db.refresh(commission)

        return commission

    # =====================================================
    # GET
    # =====================================================

    async def get_commission(
        self,
        commission_id: UUID,
    ) -> AffiliateCommission:

        commission = await self.db.get(
            AffiliateCommission,
            commission_id,
        )

        if commission is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Commission not found.",
            )

        return commission

    # =====================================================
    # LIST
    # =====================================================

    async def list_commissions(
        self,
    ) -> list[AffiliateCommission]:

        result = await self.db.execute(
            select(AffiliateCommission).order_by(
                AffiliateCommission.created_at.desc()
            )
        )

        return list(result.scalars().all())
    
    # =====================================================
    # UPDATE
    # =====================================================

    async def update_commission(
        self,
        commission_id: UUID,
        payload: AffiliateCommissionUpdate,
    ) -> AffiliateCommission:

        commission = await self.get_commission(
            commission_id
        )

        update_data = payload.model_dump(
            exclude_unset=True,
            exclude_none=True,
        )

        for key, value in update_data.items():
            setattr(commission, key, value)

        await self.db.commit()
        await self.db.refresh(commission)

        return commission

    # =====================================================
    # APPROVE
    # =====================================================

    async def approve_commission(
        self,
        commission_id: UUID,
        approved_by: str,
    ) -> AffiliateCommission:

        commission = await self.get_commission(
            commission_id
        )

        commission.status = CommissionStatus.APPROVED
        commission.approved_by = approved_by

        await self.db.commit()
        await self.db.refresh(commission)

        return commission

    # =====================================================
    # REJECT
    # =====================================================

    async def reject_commission(
        self,
        commission_id: UUID,
        remarks: str | None = None,
    ) -> AffiliateCommission:

        commission = await self.get_commission(
            commission_id
        )

        commission.status = CommissionStatus.REJECTED

        if remarks:
            commission.remarks = remarks

        await self.db.commit()
        await self.db.refresh(commission)

        return commission
    
    # =====================================================
    # MARK AS PAID
    # =====================================================

    async def mark_as_paid(
        self,
        commission_id: UUID,
    ) -> AffiliateCommission:

        commission = await self.get_commission(
            commission_id
        )

        commission.status = CommissionStatus.PAID

        await self.db.commit()
        await self.db.refresh(commission)

        return commission

    # =====================================================
    # ASSIGN PAYOUT
    # =====================================================

    async def assign_payout(
        self,
        commission_id: UUID,
        payout_id: UUID,
    ) -> AffiliateCommission:

        commission = await self.get_commission(
            commission_id
        )

        commission.payout_id = payout_id

        await self.db.commit()
        await self.db.refresh(commission)

        return commission

    # =====================================================
    # LIST BY STATUS
    # =====================================================

    async def list_by_status(
        self,
        status: CommissionStatus,
    ) -> list[AffiliateCommission]:

        result = await self.db.execute(
            select(AffiliateCommission)
            .where(
                AffiliateCommission.status == status
            )
            .order_by(
                AffiliateCommission.created_at.desc()
            )
        )

        return list(result.scalars().all())

    # =====================================================
    # LIST BY AFFILIATE
    # =====================================================

    async def list_by_affiliate(
        self,
        affiliate_id: UUID,
    ) -> list[AffiliateCommission]:

        result = await self.db.execute(
            select(AffiliateCommission)
            .where(
                AffiliateCommission.affiliate_id == affiliate_id
            )
            .order_by(
                AffiliateCommission.created_at.desc()
            )
        )

        return list(result.scalars().all())

    # =====================================================
    # DELETE
    # =====================================================

    async def delete_commission(
        self,
        commission_id: UUID,
    ) -> None:

        commission = await self.get_commission(
            commission_id
        )

        await self.db.delete(commission)
        await self.db.commit()

    # =====================================================
    # TOTAL COMMISSION
    # =====================================================

    async def total_commission_amount(
        self,
        affiliate_id: UUID,
    ) -> int:

        result = await self.db.execute(
            select(AffiliateCommission).where(
                AffiliateCommission.affiliate_id == affiliate_id
            )
        )

        commissions = result.scalars().all()

        return sum(
            commission.commission_amount
            for commission in commissions
        )