"""Unit tests for CouponService."""
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
import pytest_asyncio

from app.models.coupon import Coupon, DiscountType
from app.schemas.coupon import CouponCreate, CouponValidationRequest
from app.services.coupon_service import CouponService

USER_ID = uuid.uuid4()
NOW = datetime.now(timezone.utc)


async def _seed_coupon(db, **kwargs) -> Coupon:
    defaults = dict(
        code="SAVE10",
        discount_type=DiscountType.PERCENT,
        discount_value=Decimal("10"),
        valid_from=NOW - timedelta(days=1),
        valid_until=NOW + timedelta(days=30),
        usage_count=0,
        per_user_limit=1,
        is_active=True,
    )
    defaults.update(kwargs)
    c = Coupon(**defaults)
    db.add(c)
    await db.flush()
    return c


class TestCouponValidation:
    @pytest.mark.asyncio
    async def test_valid_percent_discount(self, db_session):
        await _seed_coupon(db_session)
        svc = CouponService(db_session)
        result = await svc.validate_coupon(
            CouponValidationRequest(code="SAVE10", cart_total=Decimal("500")),
            USER_ID,
        )
        assert result.valid is True
        assert result.discount_amount == Decimal("50.00")
        assert result.final_total == Decimal("450.00")

    @pytest.mark.asyncio
    async def test_percent_discount_respects_cap(self, db_session):
        await _seed_coupon(db_session, max_discount_cap=Decimal("30"))
        svc = CouponService(db_session)
        result = await svc.validate_coupon(
            CouponValidationRequest(code="SAVE10", cart_total=Decimal("500")),
            USER_ID,
        )
        assert result.discount_amount == Decimal("30")

    @pytest.mark.asyncio
    async def test_fixed_discount(self, db_session):
        await _seed_coupon(
            db_session,
            code="FLAT50",
            discount_type=DiscountType.FIXED,
            discount_value=Decimal("50"),
        )
        svc = CouponService(db_session)
        result = await svc.validate_coupon(
            CouponValidationRequest(code="FLAT50", cart_total=Decimal("200")),
            USER_ID,
        )
        assert result.valid is True
        assert result.discount_amount == Decimal("50")

    @pytest.mark.asyncio
    async def test_expired_coupon(self, db_session):
        await _seed_coupon(
            db_session,
            valid_until=NOW - timedelta(days=1),
        )
        svc = CouponService(db_session)
        result = await svc.validate_coupon(
            CouponValidationRequest(code="SAVE10", cart_total=Decimal("500")),
            USER_ID,
        )
        assert result.valid is False
        assert "expired" in result.message.lower()

    @pytest.mark.asyncio
    async def test_min_order_not_met(self, db_session):
        await _seed_coupon(db_session, min_order_value=Decimal("1000"))
        svc = CouponService(db_session)
        result = await svc.validate_coupon(
            CouponValidationRequest(code="SAVE10", cart_total=Decimal("500")),
            USER_ID,
        )
        assert result.valid is False
        assert "Minimum" in result.message

    @pytest.mark.asyncio
    async def test_usage_limit_exceeded(self, db_session):
        await _seed_coupon(db_session, usage_limit=1, usage_count=1)
        svc = CouponService(db_session)
        result = await svc.validate_coupon(
            CouponValidationRequest(code="SAVE10", cart_total=Decimal("500")),
            USER_ID,
        )
        assert result.valid is False

    @pytest.mark.asyncio
    async def test_inactive_coupon(self, db_session):
        await _seed_coupon(db_session, is_active=False)
        svc = CouponService(db_session)
        result = await svc.validate_coupon(
            CouponValidationRequest(code="SAVE10", cart_total=Decimal("500")),
            USER_ID,
        )
        assert result.valid is False

    @pytest.mark.asyncio
    async def test_nonexistent_coupon(self, db_session):
        svc = CouponService(db_session)
        result = await svc.validate_coupon(
            CouponValidationRequest(code="GHOST", cart_total=Decimal("500")),
            USER_ID,
        )
        assert result.valid is False
