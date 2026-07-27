"""Unit tests for the coupon engine — creation, validation, edge cases."""
from __future__ import annotations

from decimal import Decimal

import pytest

from app.schemas import CouponCreate, CouponValidateRequest
from app.services.coupon_service import CouponService


async def _create_percent_coupon(db, code="SAVE20", value="20", min_order="500", cap=None):
    svc = CouponService(db)
    return await svc.create_coupon(
        CouponCreate(
            code=code,
            discount_type="percent",
            discount_value=Decimal(value),
            min_order_value=Decimal(min_order),
            max_discount_cap=Decimal(cap) if cap else None,
            max_uses=100,
            max_uses_per_user=1,
        )
    )


# ── Creation ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_percent_coupon(db):
    coupon = await _create_percent_coupon(db, "PCNT10")
    assert coupon.code == "PCNT10"
    assert coupon.discount_type == "percent"
    assert coupon.is_active is True


@pytest.mark.asyncio
async def test_create_fixed_coupon(db):
    svc = CouponService(db)
    coupon = await svc.create_coupon(
        CouponCreate(code="FLAT50", discount_type="fixed", discount_value=Decimal("50"))
    )
    assert coupon.code == "FLAT50"
    assert coupon.discount_type == "fixed"


@pytest.mark.asyncio
async def test_duplicate_coupon_raises_409(db):
    from fastapi import HTTPException
    await _create_percent_coupon(db, "DUP")
    with pytest.raises(HTTPException) as exc:
        await _create_percent_coupon(db, "DUP")
    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_coupon_code_uppercased(db):
    svc = CouponService(db)
    coupon = await svc.create_coupon(
        CouponCreate(code="lower10", discount_type="fixed", discount_value=Decimal("10"))
    )
    assert coupon.code == "LOWER10"


# ── Validation ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_valid_percent_coupon(db):
    await _create_percent_coupon(db, "V20", "20", "500")
    svc = CouponService(db)
    resp = await svc.validate(
        CouponValidateRequest(code="V20", order_value=Decimal("1000"), user_id="u1")
    )
    assert resp.valid is True
    assert resp.discount_amount == Decimal("200.00")
    assert resp.final_order_value == Decimal("800.00")


@pytest.mark.asyncio
async def test_percent_coupon_with_cap(db):
    await _create_percent_coupon(db, "CAP20", "20", "500", cap="150")
    svc = CouponService(db)
    resp = await svc.validate(
        CouponValidateRequest(code="CAP20", order_value=Decimal("2000"), user_id="u1")
    )
    assert resp.valid is True
    assert resp.discount_amount == Decimal("150.00")  # capped


@pytest.mark.asyncio
async def test_fixed_coupon_discount(db):
    svc = CouponService(db)
    await svc.create_coupon(
        CouponCreate(code="FIX100", discount_type="fixed", discount_value=Decimal("100"))
    )
    resp = await svc.validate(
        CouponValidateRequest(code="FIX100", order_value=Decimal("800"), user_id="u1")
    )
    assert resp.valid is True
    assert resp.discount_amount == Decimal("100.00")
    assert resp.final_order_value == Decimal("700.00")


@pytest.mark.asyncio
async def test_min_order_not_met(db):
    await _create_percent_coupon(db, "HIORD", "20", "1000")
    svc = CouponService(db)
    resp = await svc.validate(
        CouponValidateRequest(code="HIORD", order_value=Decimal("500"), user_id="u1")
    )
    assert resp.valid is False
    assert "Minimum order" in resp.message


@pytest.mark.asyncio
async def test_expired_coupon(db):
    svc = CouponService(db)
    await svc.create_coupon(
        CouponCreate(
            code="EXPIRED",
            discount_type="fixed",
            discount_value=Decimal("10"),
            valid_until="2020-01-01T00:00:00+00:00",  # past
        )
    )
    resp = await svc.validate(
        CouponValidateRequest(code="EXPIRED", order_value=Decimal("500"), user_id="u1")
    )
    assert resp.valid is False
    assert "expired" in resp.message.lower()


@pytest.mark.asyncio
async def test_nonexistent_coupon(db):
    svc = CouponService(db)
    resp = await svc.validate(
        CouponValidateRequest(code="GHOST", order_value=Decimal("500"), user_id="u1")
    )
    assert resp.valid is False
    assert "not found" in resp.message.lower()


# ── API endpoint tests ────────────────────────────────────────────────────────

def test_create_coupon_api(admin_client, coupon_payload):
    resp = admin_client.post("/api/v1/coupons", json=coupon_payload)
    assert resp.status_code == 201
    assert resp.json()["code"] == "SAVE20"


def test_list_coupons_api(admin_client, coupon_payload):
    admin_client.post("/api/v1/coupons", json={**coupon_payload, "code": "LIST1"})
    resp = admin_client.get("/api/v1/coupons")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_validate_coupon_api(customer_client, admin_client, coupon_payload):
    admin_client.post("/api/v1/coupons", json={**coupon_payload, "code": "VAPI20"})
    resp = customer_client.post(
        "/api/v1/coupons/validate",
        json={"code": "VAPI20", "order_value": "1000.00", "user_id": "user-123"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["valid"] is True
