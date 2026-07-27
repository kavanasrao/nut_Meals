"""
Affiliate Service.

Handles affiliate registration, profile management,
activation, and retrieval.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.affiliate import (
    Affiliate,
    AffiliateStatus,
)
from app.schema.affiliate import (
    AffiliateCreate,
    AffiliateUpdate,
)


class AffiliateService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # =====================================================
    # CREATE
    # =====================================================

    async def create_affiliate(
        self,
        payload: AffiliateCreate,
    ) -> Affiliate:

        existing = await self.db.scalar(
            select(Affiliate).where(
                Affiliate.customer_id == payload.customer_id
            )
        )

        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Customer is already an affiliate.",
            )

        code_exists = await self.db.scalar(
            select(Affiliate).where(
                Affiliate.affiliate_code == payload.affiliate_code
            )
        )

        if code_exists:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Affiliate code already exists.",
            )

        affiliate = Affiliate(
            customer_id=payload.customer_id,
            affiliate_code=payload.affiliate_code,
            display_name=payload.display_name,
            email=payload.email,
            phone=payload.phone,
            commission_type=payload.commission_type,
            commission_value=payload.commission_value,
            notes=payload.notes,
            created_by=payload.created_by,
        )

        self.db.add(affiliate)

        await self.db.commit()
        await self.db.refresh(affiliate)

        return affiliate

    # =====================================================
    # GET
    # =====================================================

    async def get_affiliate(
        self,
        affiliate_id: UUID,
    ) -> Affiliate:

        affiliate = await self.db.get(
            Affiliate,
            affiliate_id,
        )

        if affiliate is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Affiliate not found.",
            )

        return affiliate

    async def list_affiliates(
        self,
    ) -> list[Affiliate]:

        result = await self.db.execute(
            select(Affiliate).order_by(
                Affiliate.created_at.desc()
            )
        )

        return list(result.scalars().all())
    
    # =====================================================
    # UPDATE
    # =====================================================

    async def update_affiliate(
        self,
        affiliate_id: UUID,
        payload: AffiliateUpdate,
    ) -> Affiliate:

        affiliate = await self.get_affiliate(
            affiliate_id
        )

        update_data = payload.model_dump(
            exclude_unset=True,
            exclude_none=True,
        )

        for key, value in update_data.items():
            setattr(affiliate, key, value)

        await self.db.commit()
        await self.db.refresh(affiliate)

        return affiliate

    # =====================================================
    # ACTIVATE
    # =====================================================

    async def activate_affiliate(
        self,
        affiliate_id: UUID,
    ) -> Affiliate:

        affiliate = await self.get_affiliate(
            affiliate_id
        )

        affiliate.status = AffiliateStatus.ACTIVE
        affiliate.is_verified = True

        await self.db.commit()
        await self.db.refresh(affiliate)

        return affiliate

    # =====================================================
    # SUSPEND
    # =====================================================

    async def suspend_affiliate(
        self,
        affiliate_id: UUID,
    ) -> Affiliate:

        affiliate = await self.get_affiliate(
            affiliate_id
        )

        affiliate.status = AffiliateStatus.SUSPENDED

        await self.db.commit()
        await self.db.refresh(affiliate)

        return affiliate

    # =====================================================
    # BLOCK
    # =====================================================

    async def block_affiliate(
        self,
        affiliate_id: UUID,
    ) -> Affiliate:

        affiliate = await self.get_affiliate(
            affiliate_id
        )

        affiliate.status = AffiliateStatus.BLOCKED

        await self.db.commit()
        await self.db.refresh(affiliate)

        return affiliate

    # =====================================================
    # GET BY AFFILIATE CODE
    # =====================================================

    async def get_by_code(
        self,
        affiliate_code: str,
    ) -> Affiliate:

        affiliate = await self.db.scalar(
            select(Affiliate).where(
                Affiliate.affiliate_code == affiliate_code
            )
        )

        if affiliate is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Affiliate not found.",
            )

        return affiliate

    # =====================================================
    # LIST BY STATUS
    # =====================================================

    async def list_by_status(
        self,
        status: AffiliateStatus,
    ) -> list[Affiliate]:

        result = await self.db.execute(
            select(Affiliate)
            .where(Affiliate.status == status)
            .order_by(Affiliate.created_at.desc())
        )

        return list(result.scalars().all())

    # =====================================================
    # DELETE
    # =====================================================

    async def delete_affiliate(
        self,
        affiliate_id: UUID,
    ) -> None:

        affiliate = await self.get_affiliate(
            affiliate_id
        )

        await self.db.delete(affiliate)
        await self.db.commit()

    # =====================================================
    # DASHBOARD SUMMARY
    # =====================================================

    async def dashboard_summary(
        self,
        affiliate_id: UUID,
    ) -> dict:

        affiliate = await self.get_affiliate(
            affiliate_id
        )

        return {
            "affiliate_id": affiliate.id,
            "affiliate_code": affiliate.affiliate_code,
            "status": affiliate.status,
            "verified": affiliate.is_verified,
            "total_clicks": affiliate.total_clicks,
            "total_referrals": affiliate.total_referrals,
            "successful_referrals": affiliate.successful_referrals,
            "total_sales": affiliate.total_sales_amount,
            "commission_earned": affiliate.total_commission_earned,
            "commission_paid": affiliate.total_commission_paid,
        }

    # =====================================================
    # VERIFY
    # =====================================================

    async def verify_affiliate(
        self,
        affiliate_id: UUID,
    ) -> Affiliate:

        affiliate = await self.get_affiliate(
            affiliate_id
        )

        affiliate.is_verified = True

        await self.db.commit()
        await self.db.refresh(affiliate)

        return affiliate

    # =====================================================
    # DEACTIVATE
    # =====================================================

    async def deactivate_affiliate(
        self,
        affiliate_id: UUID,
    ) -> Affiliate:

        affiliate = await self.get_affiliate(
            affiliate_id
        )

        affiliate.status = AffiliateStatus.INACTIVE

        await self.db.commit()
        await self.db.refresh(affiliate)

        return affiliate

    # =====================================================
    # COUNT
    # =====================================================

    async def total_affiliates(self) -> int:

        result = await self.db.execute(
            select(Affiliate)
        )

        return len(result.scalars().all())