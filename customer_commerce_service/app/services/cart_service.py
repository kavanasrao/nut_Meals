"""Cart business logic."""
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.models.cart import Cart, CartItem
from app.schemas.cart import CartItemCreate, CartItemUpdate, CartResponse, CartItemResponse


class CartService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _get_or_create_cart(self, user_id: UUID) -> Cart:
        result = await self.db.execute(
            select(Cart).where(Cart.user_id == user_id, Cart.is_active == True)
        )
        cart = result.scalar_one_or_none()
        if not cart:
            cart = Cart(user_id=user_id)
            self.db.add(cart)
            await self.db.flush()
            await self.db.refresh(cart)
        return cart

    async def get_cart(self, user_id: UUID) -> CartResponse:
        cart = await self._get_or_create_cart(user_id)
        return self._to_response(cart)

    async def add_item(self, user_id: UUID, payload: CartItemCreate) -> CartResponse:
        cart = await self._get_or_create_cart(user_id)

        existing = next(
            (i for i in cart.items if i.product_id == payload.product_id), None
        )
        if existing:
            existing.quantity = min(existing.quantity + payload.quantity, 100)
            existing.unit_price = payload.unit_price
        else:
            item = CartItem(
                cart_id=cart.id,
                product_id=payload.product_id,
                product_name=payload.product_name,
                unit_price=payload.unit_price,
                quantity=payload.quantity,
                image_url=payload.image_url,
            )
            self.db.add(item)

        cart.last_activity_at = datetime.now(timezone.utc)
        await self.db.flush()
        await self.db.refresh(cart)
        return self._to_response(cart)

    async def update_item(self, user_id: UUID, item_id: UUID, payload: CartItemUpdate) -> CartResponse:
        cart = await self._get_or_create_cart(user_id)
        item = next((i for i in cart.items if i.id == item_id), None)
        if not item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart item not found")
        item.quantity = payload.quantity
        cart.last_activity_at = datetime.now(timezone.utc)
        await self.db.flush()
        await self.db.refresh(cart)
        return self._to_response(cart)

    async def remove_item(self, user_id: UUID, item_id: UUID) -> CartResponse:
        cart = await self._get_or_create_cart(user_id)
        item = next((i for i in cart.items if i.id == item_id), None)
        if not item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart item not found")
        await self.db.delete(item)
        await self.db.flush()
        await self.db.refresh(cart)
        return self._to_response(cart)

    async def clear_cart(self, user_id: UUID) -> None:
        cart = await self._get_or_create_cart(user_id)
        for item in list(cart.items):
            await self.db.delete(item)
        cart.coupon_code = None
        await self.db.flush()
        self.db.expire(cart)  # force relationship reload on next access

    async def apply_coupon(self, user_id: UUID, coupon_code: str) -> CartResponse:
        cart = await self._get_or_create_cart(user_id)
        cart.coupon_code = coupon_code
        await self.db.flush()
        return self._to_response(cart)

    def _to_response(self, cart: Cart) -> CartResponse:
        items = [CartItemResponse.from_orm_with_total(i) for i in (cart.items or [])]
        subtotal = sum(i.line_total for i in items)
        return CartResponse(
            id=cart.id,
            user_id=cart.user_id,
            items=items,
            coupon_code=cart.coupon_code,
            subtotal=subtotal,
            is_active=cart.is_active,
        )
