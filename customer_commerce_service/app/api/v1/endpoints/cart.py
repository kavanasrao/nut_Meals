"""Cart API endpoints."""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import TokenPayload, require_customer
from app.db.session import get_db
from app.schemas.cart import (
    ApplyCouponRequest, CartItemCreate, CartItemUpdate, CartResponse
)
from app.services.cart_service import CartService

router = APIRouter(prefix="/cart", tags=["Cart"])
CurrentUser = Annotated[TokenPayload, Depends(require_customer)]


@router.get("", response_model=CartResponse, summary="Get current user's cart")
async def get_cart(user: CurrentUser, db: AsyncSession = Depends(get_db)):
    return await CartService(db).get_cart(user.user_id)


@router.post("/items", response_model=CartResponse, status_code=201,
             summary="Add item to cart (upserts if same product)")
async def add_item(
    payload: CartItemCreate, user: CurrentUser, db: AsyncSession = Depends(get_db)
):
    return await CartService(db).add_item(user.user_id, payload)


@router.patch("/items/{item_id}", response_model=CartResponse, summary="Update item quantity")
async def update_item(
    item_id: UUID,
    payload: CartItemUpdate,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    return await CartService(db).update_item(user.user_id, item_id, payload)


@router.delete("/items/{item_id}", response_model=CartResponse, summary="Remove item from cart")
async def remove_item(
    item_id: UUID, user: CurrentUser, db: AsyncSession = Depends(get_db)
):
    return await CartService(db).remove_item(user.user_id, item_id)


@router.delete("", status_code=204, summary="Clear entire cart")
async def clear_cart(user: CurrentUser, db: AsyncSession = Depends(get_db)):
    await CartService(db).clear_cart(user.user_id)


@router.post("/coupon", response_model=CartResponse, summary="Apply coupon to cart")
async def apply_coupon(
    payload: ApplyCouponRequest, user: CurrentUser, db: AsyncSession = Depends(get_db)
):
    return await CartService(db).apply_coupon(user.user_id, payload.coupon_code)
