"""Unit tests: addresses, wishlist, invoices."""
from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest

from app.schemas import AddressCreate, WishlistItemCreate, InvoiceCreate, InvoiceItemIn
from app.services.address_service import AddressService
from app.services.wishlist_service import WishlistService
from app.services.invoice_service import InvoiceService


# ══════════════════════════════════════════════════════════════════════════════
# ADDRESSES
# ══════════════════════════════════════════════════════════════════════════════

def _addr(label="Home", is_default=False):
    return AddressCreate(
        label=label,
        full_name="Test User",
        phone="9999999999",
        line1="123 Main St",
        city="Bengaluru",
        state="Karnataka",
        pincode="560001",
        is_default=is_default,
    )


@pytest.mark.asyncio
async def test_create_address(db):
    svc = AddressService(db)
    addr = await svc.create("u1", _addr())
    assert addr.city == "Bengaluru"
    assert addr.user_id == "u1"


@pytest.mark.asyncio
async def test_list_addresses(db):
    svc = AddressService(db)
    await svc.create("u2", _addr("Home"))
    await svc.create("u2", _addr("Office"))
    addrs = await svc.list_addresses("u2")
    assert len(addrs) == 2


@pytest.mark.asyncio
async def test_set_default_address_clears_others(db):
    svc = AddressService(db)
    a1 = await svc.create("u3", _addr("Home", is_default=True))
    a2 = await svc.create("u3", _addr("Office"))
    await svc.set_default("u3", a2.id)

    addrs = await svc.list_addresses("u3")
    defaults = [a for a in addrs if a.is_default]
    assert len(defaults) == 1
    assert defaults[0].id == a2.id


@pytest.mark.asyncio
async def test_delete_address(db):
    svc = AddressService(db)
    addr = await svc.create("u4", _addr())
    await svc.delete("u4", addr.id)
    addrs = await svc.list_addresses("u4")
    assert len(addrs) == 0


@pytest.mark.asyncio
async def test_get_wrong_user_address_raises_404(db):
    from fastapi import HTTPException
    svc = AddressService(db)
    addr = await svc.create("u5", _addr())
    with pytest.raises(HTTPException) as exc:
        await svc.get("other-user", addr.id)
    assert exc.value.status_code == 404


# API

def test_address_crud_api(customer_client, address_payload):
    # Create
    r = customer_client.post("/api/v1/addresses", json=address_payload)
    assert r.status_code == 201
    addr_id = r.json()["id"]

    # List
    r = customer_client.get("/api/v1/addresses")
    assert r.status_code == 200
    assert len(r.json()) >= 1

    # Update
    r = customer_client.patch(f"/api/v1/addresses/{addr_id}", json={"city": "Mumbai"})
    assert r.status_code == 200
    assert r.json()["city"] == "Mumbai"

    # Delete
    r = customer_client.delete(f"/api/v1/addresses/{addr_id}")
    assert r.status_code == 204


# ══════════════════════════════════════════════════════════════════════════════
# WISHLIST
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_add_to_wishlist(db):
    svc = WishlistService(db)
    item = await svc.add(
        "w1", WishlistItemCreate(product_id="p1", product_name="Granola", unit_price=Decimal("199"))
    )
    assert item.product_id == "p1"


@pytest.mark.asyncio
async def test_add_duplicate_is_idempotent(db):
    svc = WishlistService(db)
    await svc.add("w2", WishlistItemCreate(product_id="p2", product_name="Muesli", unit_price=Decimal("299")))
    await svc.add("w2", WishlistItemCreate(product_id="p2", product_name="Muesli", unit_price=Decimal("299")))
    items = await svc.list_items("w2")
    assert len(items) == 1


@pytest.mark.asyncio
async def test_remove_from_wishlist(db):
    svc = WishlistService(db)
    await svc.add("w3", WishlistItemCreate(product_id="p3", product_name="Oats", unit_price=Decimal("99")))
    await svc.remove("w3", "p3")
    items = await svc.list_items("w3")
    assert len(items) == 0


def test_wishlist_api(customer_client):
    payload = {"product_id": "wl-prod", "product_name": "Peanut Butter", "unit_price": "299.00"}
    r = customer_client.post("/api/v1/wishlist", json=payload)
    assert r.status_code == 201

    r = customer_client.get("/api/v1/wishlist")
    assert r.status_code == 200
    assert any(i["product_id"] == "wl-prod" for i in r.json())

    r = customer_client.delete("/api/v1/wishlist/wl-prod")
    assert r.status_code == 204


# ══════════════════════════════════════════════════════════════════════════════
# INVOICES
# ══════════════════════════════════════════════════════════════════════════════

def _invoice_create_payload(order_id="order-1", user_id="user-123"):
    return InvoiceCreate(
        order_id=order_id,
        user_id=user_id,
        items=[
            InvoiceItemIn(
                product_id="prod-a",
                product_name="Nut Mix",
                quantity=2,
                unit_price=Decimal("500"),
                gst_rate=Decimal("18"),
            )
        ],
        discount_amount=Decimal("0"),
        buyer_name="Test Buyer",
        buyer_address="123 Test St",
    )


@pytest.mark.asyncio
async def test_create_invoice_calculates_gst(db):
    svc = InvoiceService(db)
    inv = await svc.create_invoice(_invoice_create_payload())
    assert inv.subtotal == Decimal("1000.00")
    assert inv.taxable_amount == Decimal("1000.00")
    # 18% GST → 9% CGST + 9% SGST
    assert inv.cgst_amount == Decimal("90.00")
    assert inv.sgst_amount == Decimal("90.00")
    assert inv.total_amount == Decimal("1180.00")


@pytest.mark.asyncio
async def test_duplicate_invoice_raises_409(db):
    from fastapi import HTTPException
    svc = InvoiceService(db)
    await svc.create_invoice(_invoice_create_payload("order-dup"))
    with pytest.raises(HTTPException) as exc:
        await svc.create_invoice(_invoice_create_payload("order-dup"))
    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_invoice_with_discount(db):
    svc = InvoiceService(db)
    payload = _invoice_create_payload("order-disc")
    payload.discount_amount = Decimal("100")
    inv = await svc.create_invoice(payload)
    assert inv.discount_amount == Decimal("100.00")
    assert inv.taxable_amount == Decimal("900.00")


@pytest.mark.asyncio
async def test_generate_pdf_returns_bytes(db):
    svc = InvoiceService(db)
    inv = await svc.create_invoice(_invoice_create_payload("order-pdf"))
    pdf = await svc.generate_pdf(inv.id)
    assert isinstance(pdf, bytes)
    assert pdf[:4] == b"%PDF"  # PDF magic bytes
