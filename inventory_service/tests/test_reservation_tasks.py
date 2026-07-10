"""Unit tests for the reservation sweep service function (exercised
directly, since the Celery task wrapper itself is a thin sync bridge)."""
import pytest
from datetime import datetime, timedelta, timezone

from app.models.reservation import ReservationStatus, StockReservation
from app.services import reservation_service

pytestmark = pytest.mark.asyncio


async def test_release_expired_reservations_releases_only_expired(
    db_session, seeded_warehouse, seeded_items
):
    now = datetime.now(timezone.utc)

    expired = StockReservation(
        order_id="ORDER-EXPIRED", item_id=seeded_items["bar"].id, warehouse_id=seeded_warehouse.id,
        quantity=1, status=ReservationStatus.ACTIVE, expires_at=now - timedelta(minutes=1),
    )
    active = StockReservation(
        order_id="ORDER-ACTIVE", item_id=seeded_items["bar"].id, warehouse_id=seeded_warehouse.id,
        quantity=1, status=ReservationStatus.ACTIVE, expires_at=now + timedelta(minutes=30),
    )
    db_session.add_all([expired, active])
    await db_session.commit()

    released_count = await reservation_service.release_expired_reservations(db_session)
    assert released_count == 1

    await db_session.refresh(expired)
    await db_session.refresh(active)
    assert expired.status == ReservationStatus.RELEASED
    assert active.status == ReservationStatus.ACTIVE
