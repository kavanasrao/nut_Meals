"""Coupon engine — validation, creation, usage tracking."""
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.models.coupon import Coupon, CouponUsage, DiscountType
from app.schemas.coupon import (
    CouponCreate, CouponResponse,
    CouponValidationRequest, CouponValidationResponse,
)


def _as_utc(dt: datetime) -> datetime:
    """Normalise a datetime to UTC, adding tzinfo if it's naive (SQLite test DB)."""
    if dt is None:
        return dt
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


class CouponService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_coupon(self, payload: CouponCreate) -> CouponResponse:
        existing = await self.db.execute(
            select(Coupon).where(Coupon.code == payload.code.upper())
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Coupon code already exists")

        coupon = Coupon(
            code=payload.code.upper(),
            description=payload.description,
            discount_type=payload.discount_type,
            discount_value=payload.discount_value,
            min_order_value=payload.min_order_value,
            max_discount_cap=payload.max_discount_cap,
            usage_limit=payload.usage_limit,
            per_user_limit=payload.per_user_limit,
            valid_from=payload.valid_from,
            valid_until=payload.valid_until,
        )
        self.db.add(coupon)
        await self.db.flush()
        return CouponResponse.model_validate(coupon)

    async def get_coupon(self, code: str) -> CouponResponse:
        result = await self.db.execute(
            select(Coupon).where(Coupon.code == code.upper())
        )
        coupon = result.scalar_one_or_none()
        if not coupon:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Coupon not found")
        return CouponResponse.model_validate(coupon)

    async def validate_coupon(
        self, payload: CouponValidationRequest, user_id: UUID
    ) -> CouponValidationResponse:
        result = await self.db.execute(
            select(Coupon).where(Coupon.code == payload.code.upper())
        )
        coupon = result.scalar_one_or_none()
        now = datetime.now(timezone.utc)

        def fail(msg: str) -> CouponValidationResponse:
            return CouponValidationResponse(
                valid=False,
                discount_amount=Decimal("0"),
                final_total=payload.cart_total,
                message=msg,
            )

        if not coupon or not coupon.is_active:
            return fail("Coupon is invalid or inactive")
        if _as_utc(coupon.valid_from) > now:
            return fail("Coupon is not yet valid")
        if coupon.valid_until and _as_utc(coupon.valid_until) < now:
            return fail("Coupon has expired")
        if coupon.usage_limit and coupon.usage_count >= coupon.usage_limit:
            return fail("Coupon usage limit reached")
        if coupon.min_order_value and payload.cart_total < coupon.min_order_value:
            return fail(f"Minimum order value ₹{coupon.min_order_value} required")

        usage_result = await self.db.execute(
            select(CouponUsage).where(
                CouponUsage.coupon_id == coupon.id,
                CouponUsage.user_id == user_id,
            )
        )
        usage = usage_result.scalar_one_or_none()
        if usage and usage.times_used >= coupon.per_user_limit:
            return fail("You have already used this coupon the maximum number of times")

        if coupon.discount_type == DiscountType.PERCENT:
            discount = (payload.cart_total * coupon.discount_value / 100).quantize(Decimal("0.01"))
            if coupon.max_discount_cap:
                discount = min(discount, coupon.max_discount_cap)
        else:
            discount = min(coupon.discount_value, payload.cart_total)

        return CouponValidationResponse(
            valid=True,
            discount_amount=discount,
            final_total=payload.cart_total - discount,
            message="Coupon applied successfully",
        )

    async def record_usage(self, coupon_code: str, user_id: UUID, order_id: UUID) -> None:
        result = await self.db.execute(
            select(Coupon).where(Coupon.code == coupon_code.upper())
        )
        coupon = result.scalar_one_or_none()
        if not coupon:
            return
        coupon.usage_count += 1
        usage_result = await self.db.execute(
            select(CouponUsage).where(
                CouponUsage.coupon_id == coupon.id,
                CouponUsage.user_id == user_id,
            )
        )
        usage = usage_result.scalar_one_or_none()
        if usage:
            usage.times_used += 1
            usage.order_id = order_id
        else:
            self.db.add(CouponUsage(coupon_id=coupon.id, user_id=user_id, order_id=order_id))
        await self.db.flush()
