"""Wishlist API endpoints."""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import TokenPayload, require_customer
from app.db.session import get_db
from app.schemas.wishlist import WishlistItemCreate, WishlistItemResponse, WishlistResponse
from app.services.wishlist_service import WishlistService

router = APIRouter(prefix="/wishlist", tags=["Wishlist"])
CurrentUser = Annotated[TokenPayload, Depends(require_customer)]


@router.get("", response_model=WishlistResponse, summary="Get wishlist")
async def get_wishlist(user: CurrentUser, db: AsyncSession = Depends(get_db)):
    return await WishlistService(db).get_wishlist(user.user_id)


@router.post("", response_model=WishlistItemResponse, status_code=201,
             summary="Add product to wishlist")
async def add_to_wishlist(
    payload: WishlistItemCreate, user: CurrentUser, db: AsyncSession = Depends(get_db)
):
    return await WishlistService(db).add_item(user.user_id, payload)


@router.delete("/{product_id}", status_code=204, summary="Remove product from wishlist")
async def remove_from_wishlist(
    product_id: UUID, user: CurrentUser, db: AsyncSession = Depends(get_db)
):
    await WishlistService(db).remove_item(user.user_id, product_id)
