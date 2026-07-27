"""
Affiliate Coupon API routes.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.affiliate_coupon import (
    AffiliateCouponCreate,
    AffiliateCouponResponse,
    AffiliateCouponUpdate,
)
from app.services.coupon_service import CouponService

router = APIRouter(
    prefix="/affiliate-coupons",
    tags=["Affiliate Coupons"],
)


# ==========================================================
# CREATE
# ==========================================================

@router.post(
    "",
    response_model=AffiliateCouponResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_coupon(
    payload: AffiliateCouponCreate,
    db: AsyncSession = Depends(get_db),
):
    service = CouponService(db)
    return await service.create_coupon(payload)


# ==========================================================
# LIST
# ==========================================================

@router.get(
    "",
    response_model=list[AffiliateCouponResponse],
)
async def list_coupons(
    db: AsyncSession = Depends(get_db),
):
    service = CouponService(db)
    return await service.list_coupons()


# ==========================================================
# GET
# ==========================================================

@router.get(
    "/{coupon_id}",
    response_model=AffiliateCouponResponse,
)
async def get_coupon(
    coupon_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    service = CouponService(db)
    return await service.get_coupon(coupon_id)


# ==========================================================
# GET BY CODE
# ==========================================================

@router.get(
    "/code/{coupon_code}",
    response_model=AffiliateCouponResponse,
)
async def get_coupon_by_code(
    coupon_code: str,
    db: AsyncSession = Depends(get_db),
):
    service = CouponService(db)
    return await service.get_by_code(coupon_code)


# ==========================================================
# UPDATE
# ==========================================================

@router.put(
    "/{coupon_id}",
    response_model=AffiliateCouponResponse,
)
async def update_coupon(
    coupon_id: UUID,
    payload: AffiliateCouponUpdate,
    db: AsyncSession = Depends(get_db),
):
    service = CouponService(db)
    return await service.update_coupon(
        coupon_id,
        payload,
    )


# ==========================================================
# ACTIVATE
# ==========================================================

@router.patch(
    "/{coupon_id}/activate",
    response_model=AffiliateCouponResponse,
)
async def activate_coupon(
    coupon_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    service = CouponService(db)
    return await service.activate_coupon(coupon_id)


# ==========================================================
# DEACTIVATE
# ==========================================================

@router.patch(
    "/{coupon_id}/deactivate",
    response_model=AffiliateCouponResponse,
)
async def deactivate_coupon(
    coupon_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    service = CouponService(db)
    return await service.deactivate_coupon(coupon_id)


# ==========================================================
# EXPIRE
# ==========================================================

@router.patch(
    "/{coupon_id}/expire",
    response_model=AffiliateCouponResponse,
)
async def expire_coupon(
    coupon_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    service = CouponService(db)
    return await service.expire_coupon(coupon_id)

# ==========================================================
# INCREMENT USAGE
# ==========================================================

@router.patch(
    "/{coupon_id}/increment-usage",
    response_model=AffiliateCouponResponse,
)
async def increment_usage(
    coupon_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    service = CouponService(db)
    return await service.increment_usage(coupon_id)


# ==========================================================
# DELETE
# ==========================================================

@router.delete(
    "/{coupon_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_coupon(
    coupon_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    service = CouponService(db)

    await service.delete_coupon(coupon_id)

    return Response(
        status_code=status.HTTP_204_NO_CONTENT,
    )