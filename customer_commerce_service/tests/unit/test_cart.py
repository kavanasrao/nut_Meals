"""Unit tests for cart service and cart API endpoints."""
from __future__ import annotations

from decimal import Decimal

import pytest
import pytest_asyncio

from app.models import Cart, CartItem
from app.schemas import CartItemCreate, CartItemUpdate
from app.services.cart_service import CartService


# ── Service-layer tests ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_cart_creates_empty_cart(db):
    svc = CartService(db)
    cart = await svc.get_cart("user-new")
    assert cart.user_id == "user-new"
    assert cart.items == []
    assert cart.subtotal == Decimal("0")


@pytest.mark.asyncio
async def test_add_item_to_cart(db):
    svc = CartService(db)
    payload = CartItemCreate(
        product_id="prod-1", product_name="Cashew Mix", quantity=3, unit_price=Decimal("200")
    )
    cart = await svc.add_item("user-1", payload)
    assert len(cart.items) == 1
    assert cart.items[0].product_id == "prod-1"
    assert cart.items[0].quantity == 3
    assert cart.subtotal == Decimal("600")


@pytest.mark.asyncio
async def test_add_same_item_merges_quantity(db):
    svc = CartService(db)
    payload = CartItemCreate(
        product_id="prod-2", product_name="Walnut", quantity=2, unit_price=Decimal("150")
    )
    await svc.add_item("user-2", payload)
    # Add again
    cart = await svc.add_item("user-2", payload)
    assert len(cart.items) == 1
    assert cart.items[0].quantity == 4  # merged


@pytest.mark.asyncio
async def test_update_cart_item_quantity(db):
    svc = CartService(db)
    payload = CartItemCreate(
        product_id="prod-3", product_name="Pistachio", quantity=1, unit_price=Decimal("300")
    )
    cart = await svc.add_item("user-3", payload)
    item_id = cart.items[0].id

    updated = await svc.update_item("user-3", item_id, CartItemUpdate(quantity=5))
    assert updated.items[0].quantity == 5
    assert updated.subtotal == Decimal("1500")


@pytest.mark.asyncio
async def test_remove_cart_item(db):
    svc = CartService(db)
    payload = CartItemCreate(
        product_id="prod-4", product_name="Dates", quantity=2, unit_price=Decimal("100")
    )
    cart = await svc.add_item("user-4", payload)
    item_id = cart.items[0].id

    cart = await svc.remove_item("user-4", item_id)
    assert cart.items == []


@pytest.mark.asyncio
async def test_remove_nonexistent_item_raises_404(db):
    from fastapi import HTTPException
    svc = CartService(db)
    await svc.get_cart("user-5")
    with pytest.raises(HTTPException) as exc:
        await svc.remove_item("user-5", "nonexistent-id")
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_clear_cart(db):
    svc = CartService(db)
    for i in range(3):
        await svc.add_item(
            "user-6",
            CartItemCreate(
                product_id=f"prod-{i}", product_name=f"Item {i}",
                quantity=1, unit_price=Decimal("100")
            ),
        )
    await svc.clear_cart("user-6")
    cart = await svc.get_cart("user-6")
    assert cart.items == []


# ── API endpoint tests ────────────────────────────────────────────────────────

def test_get_cart_endpoint(customer_client):
    resp = customer_client.get("/api/v1/cart")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "subtotal" in data


def test_add_item_endpoint(customer_client, cart_item_payload):
    resp = customer_client.post("/api/v1/cart/items", json=cart_item_payload)
    assert resp.status_code == 201
    data = resp.json()
    assert len(data["items"]) >= 1
    assert data["items"][0]["product_id"] == "prod-abc"


def test_update_item_endpoint(customer_client, cart_item_payload):
    # Add item first
    resp = customer_client.post("/api/v1/cart/items", json=cart_item_payload)
    item_id = resp.json()["items"][0]["id"]

    resp = customer_client.patch(f"/api/v1/cart/items/{item_id}", json={"quantity": 5})
    assert resp.status_code == 200
    assert resp.json()["items"][0]["quantity"] == 5


def test_delete_item_endpoint(customer_client, cart_item_payload):
    resp = customer_client.post("/api/v1/cart/items", json=cart_item_payload)
    item_id = resp.json()["items"][0]["id"]

    resp = customer_client.delete(f"/api/v1/cart/items/{item_id}")
    assert resp.status_code == 200
    assert resp.json()["items"] == []


def test_clear_cart_endpoint(customer_client, cart_item_payload):
    customer_client.post("/api/v1/cart/items", json=cart_item_payload)
    resp = customer_client.delete("/api/v1/cart")
    assert resp.status_code == 204
