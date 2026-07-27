"""
Affiliate Coupon Service.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.affiliate_coupon import (
    AffiliateCoupon,
    CouponStatus,
)
from app.schema.affiliate_coupon import (
    AffiliateCouponCreate,
    AffiliateCouponUpdate,
)


class CouponService:
    def __init__(
        self,
        db: AsyncSession,
    ):
        self.db = db

    # =====================================================
    # CREATE
    # =====================================================

    async def create_coupon(
        self,
        payload: AffiliateCouponCreate,
    ) -> AffiliateCoupon:

        existing = await self.db.scalar(
            select(AffiliateCoupon).where(
                AffiliateCoupon.coupon_code == payload.coupon_code
            )
        )

        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Coupon code already exists.",
            )

        coupon = AffiliateCoupon(
            affiliate_id=payload.affiliate_id,
            coupon_code=payload.coupon_code,
            title=payload.title,
            discount_type=payload.discount_type,
            discount_value=payload.discount_value,
            minimum_order_amount=payload.minimum_order_amount,
            maximum_discount_amount=payload.maximum_discount_amount,
            usage_limit=payload.usage_limit,
            is_public=payload.is_public,
            valid_from=payload.valid_from,
            valid_until=payload.valid_until,
            created_by=payload.created_by,
        )

        self.db.add(coupon)

        await self.db.commit()
        await self.db.refresh(coupon)

        return coupon

    # =====================================================
    # GET
    # =====================================================

    async def get_coupon(
        self,
        coupon_id: UUID,
    ) -> AffiliateCoupon:

        coupon = await self.db.get(
            AffiliateCoupon,
            coupon_id,
        )

        if coupon is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Coupon not found.",
            )

        return coupon

    # =====================================================
    # GET BY CODE
    # =====================================================

    async def get_by_code(
        self,
        coupon_code: str,
    ) -> AffiliateCoupon:

        coupon = await self.db.scalar(
            select(AffiliateCoupon).where(
                AffiliateCoupon.coupon_code == coupon_code
            )
        )

        if coupon is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Coupon not found.",
            )

        return coupon

    # =====================================================
    # LIST
    # =====================================================

    async def list_coupons(
        self,
    ) -> list[AffiliateCoupon]:

        result = await self.db.execute(
            select(AffiliateCoupon).order_by(
                AffiliateCoupon.created_at.desc()
            )
        )

        return list(result.scalars().all())

    # =====================================================
    # UPDATE
    # =====================================================

    async def update_coupon(
        self,
        coupon_id: UUID,
        payload: AffiliateCouponUpdate,
    ) -> AffiliateCoupon:

        coupon = await self.get_coupon(
            coupon_id
        )

        update_data = payload.model_dump(
            exclude_none=True,
            exclude_unset=True,
        )

        for key, value in update_data.items():
            setattr(coupon, key, value)

        await self.db.commit()
        await self.db.refresh(coupon)

        return coupon

    # =====================================================
    # ACTIVATE
    # =====================================================

    async def activate_coupon(
        self,
        coupon_id: UUID,
    ) -> AffiliateCoupon:

        coupon = await self.get_coupon(
            coupon_id
        )

        coupon.status = CouponStatus.ACTIVE

        await self.db.commit()
        await self.db.refresh(coupon)

        return coupon

    # =====================================================
    # DEACTIVATE
    # =====================================================

    async def deactivate_coupon(
        self,
        coupon_id: UUID,
    ) -> AffiliateCoupon:

        coupon = await self.get_coupon(
            coupon_id
        )

        coupon.status = CouponStatus.INACTIVE

        await self.db.commit()
        await self.db.refresh(coupon)

        return coupon

    # =====================================================
    # EXPIRE
    # =====================================================

    async def expire_coupon(
        self,
        coupon_id: UUID,
    ) -> AffiliateCoupon:

        coupon = await self.get_coupon(
            coupon_id
        )

        coupon.status = CouponStatus.EXPIRED

        await self.db.commit()
        await self.db.refresh(coupon)

        return coupon

    # =====================================================
    # INCREMENT USAGE
    # =====================================================

    async def increment_usage(
        self,
        coupon_id: UUID,
    ) -> AffiliateCoupon:

        coupon = await self.get_coupon(
            coupon_id
        )

        coupon.usage_count += 1

        await self.db.commit()
        await self.db.refresh(coupon)

        return coupon

    # =====================================================
    # LIST BY AFFILIATE
    # =====================================================

    async def list_by_affiliate(
        self,
        affiliate_id: UUID,
    ) -> list[AffiliateCoupon]:

        result = await self.db.execute(
            select(AffiliateCoupon)
            .where(
                AffiliateCoupon.affiliate_id == affiliate_id
            )
            .order_by(
                AffiliateCoupon.created_at.desc()
            )
        )

        return list(result.scalars().all())

    # =====================================================
    # DELETE
    # =====================================================

    async def delete_coupon(
        self,
        coupon_id: UUID,
    ) -> None:

        coupon = await self.get_coupon(
            coupon_id
        )

        await self.db.delete(coupon)
        await self.db.commit()