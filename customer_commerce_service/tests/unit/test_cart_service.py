"""Unit tests for CartService."""
import uuid
from decimal import Decimal

import pytest

from app.schemas.cart import CartItemCreate, CartItemUpdate
from app.services.cart_service import CartService

USER_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
PRODUCT_ID = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
PRODUCT_ID_2 = uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")


def _item(product_id=None, qty=1, price="100.00"):
    return CartItemCreate(
        product_id=product_id or PRODUCT_ID,
        product_name="Almond Butter",
        unit_price=Decimal(price),
        quantity=qty,
    )


class TestCartService:
    @pytest.mark.asyncio
    async def test_empty_cart_created_on_first_get(self, db_session):
        svc = CartService(db_session)
        cart = await svc.get_cart(USER_ID)
        assert cart.items == []
        assert cart.subtotal == Decimal("0")

    @pytest.mark.asyncio
    async def test_add_item(self, db_session):
        svc = CartService(db_session)
        cart = await svc.add_item(USER_ID, _item())
        assert len(cart.items) == 1
        assert cart.subtotal == Decimal("100.00")

    @pytest.mark.asyncio
    async def test_add_same_product_upserts_quantity(self, db_session):
        svc = CartService(db_session)
        await svc.add_item(USER_ID, _item(qty=2))
        cart = await svc.add_item(USER_ID, _item(qty=3))
        assert len(cart.items) == 1
        assert cart.items[0].quantity == 5

    @pytest.mark.asyncio
    async def test_add_two_different_products(self, db_session):
        svc = CartService(db_session)
        await svc.add_item(USER_ID, _item())
        cart = await svc.add_item(USER_ID, _item(product_id=PRODUCT_ID_2))
        assert len(cart.items) == 2

    @pytest.mark.asyncio
    async def test_update_item_quantity(self, db_session):
        svc = CartService(db_session)
        cart = await svc.add_item(USER_ID, _item())
        item_id = cart.items[0].id
        cart = await svc.update_item(USER_ID, item_id, CartItemUpdate(quantity=7))
        assert cart.items[0].quantity == 7
        assert cart.subtotal == Decimal("700.00")

    @pytest.mark.asyncio
    async def test_remove_item(self, db_session):
        svc = CartService(db_session)
        cart = await svc.add_item(USER_ID, _item())
        item_id = cart.items[0].id
        cart = await svc.remove_item(USER_ID, item_id)
        assert cart.items == []

    @pytest.mark.asyncio
    async def test_remove_nonexistent_item_raises(self, db_session):
        from fastapi import HTTPException
        svc = CartService(db_session)
        await svc.add_item(USER_ID, _item())
        with pytest.raises(HTTPException) as exc_info:
            await svc.remove_item(USER_ID, uuid.uuid4())
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_clear_cart(self, db_session):
        svc = CartService(db_session)
        await svc.add_item(USER_ID, _item())
        await svc.clear_cart(USER_ID)
        db_session.expire_all()
        cart = await svc.get_cart(USER_ID)
        assert cart.items == []

    @pytest.mark.asyncio
    async def test_apply_coupon(self, db_session):
        svc = CartService(db_session)
        cart = await svc.apply_coupon(USER_ID, "SAVE10")
        assert cart.coupon_code == "SAVE10"


class TestCartClear:
    @pytest.mark.asyncio
    async def test_clear_then_get_is_empty(self, db_session):
        svc = CartService(db_session)
        await svc.add_item(USER_ID, _item())
        await svc.clear_cart(USER_ID)
        db_session.expire_all()  # sync call — clears identity map cache
        cart = await svc.get_cart(USER_ID)
        assert cart.items == []
        assert cart.subtotal == Decimal("0")
