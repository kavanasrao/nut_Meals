"""Wishlist business logic."""
from uuid import UUID

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.models.wishlist import WishlistItem
from app.schemas.wishlist import WishlistItemCreate, WishlistItemResponse, WishlistResponse


class WishlistService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_wishlist(self, user_id: UUID) -> WishlistResponse:
        result = await self.db.execute(
            select(WishlistItem).where(WishlistItem.user_id == user_id)
        )
        items = result.scalars().all()
        return WishlistResponse(
            items=[WishlistItemResponse.model_validate(i) for i in items],
            total=len(items),
        )

    async def add_item(self, user_id: UUID, payload: WishlistItemCreate) -> WishlistItemResponse:
        # Idempotent — ignore duplicate
        result = await self.db.execute(
            select(WishlistItem).where(
                WishlistItem.user_id == user_id,
                WishlistItem.product_id == payload.product_id,
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            return WishlistItemResponse.model_validate(existing)

        item = WishlistItem(
            user_id=user_id,
            product_id=payload.product_id,
            product_name=payload.product_name,
            unit_price=payload.unit_price,
            image_url=payload.image_url,
        )
        self.db.add(item)
        await self.db.flush()
        return WishlistItemResponse.model_validate(item)

    async def remove_item(self, user_id: UUID, product_id: UUID) -> None:
        result = await self.db.execute(
            delete(WishlistItem).where(
                WishlistItem.user_id == user_id,
                WishlistItem.product_id == product_id,
            ).returning(WishlistItem.id)
        )
        if not result.fetchone():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not in wishlist")
