"""Coupon API endpoints."""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import TokenPayload, require_admin, require_customer
from app.db.session import get_db
from app.schemas.coupon import (
    CouponCreate, CouponResponse, CouponValidationRequest, CouponValidationResponse
)
from app.services.coupon_service import CouponService

router = APIRouter(prefix="/coupons", tags=["Coupons"])
CurrentUser = Annotated[TokenPayload, Depends(require_customer)]
AdminUser = Annotated[TokenPayload, Depends(require_admin)]


@router.post("", response_model=CouponResponse, status_code=201,
             summary="Create a coupon (admin only)")
async def create_coupon(
    payload: CouponCreate, user: AdminUser, db: AsyncSession = Depends(get_db)
):
    return await CouponService(db).create_coupon(payload)


@router.get("/{code}", response_model=CouponResponse, summary="Get coupon details (admin only)")
async def get_coupon(code: str, user: AdminUser, db: AsyncSession = Depends(get_db)):
    return await CouponService(db).get_coupon(code)


@router.post("/validate", response_model=CouponValidationResponse,
             summary="Validate coupon against cart total")
async def validate_coupon(
    payload: CouponValidationRequest, user: CurrentUser, db: AsyncSession = Depends(get_db)
):
    return await CouponService(db).validate_coupon(payload, user.user_id)
