"""Unit tests for app.services.tracking."""
import uuid
from unittest.mock import AsyncMock

import pytest

from app.models.shipment import Shipment, ShipmentStatus, ShipmentType
from app.services import tracking as tracking_module


@pytest.mark.asyncio
async def test_sync_updates_status_and_creates_events(
    db_session, seeded_carriers, monkeypatch, fake_adapter_factory
):
    adapter = fake_adapter_factory("delhivery", awb="DL-999")
    monkeypatch.setattr(tracking_module, "get_adapter", lambda code: adapter)
    monkeypatch.setattr(tracking_module, "sync_order_shipment_status", AsyncMock(return_value=True))
    monkeypatch.setattr(tracking_module, "notify_shipment_status_change", AsyncMock(return_value=None))

    shipment = Shipment(
        id=uuid.uuid4(),
        order_id=uuid.uuid4(),
        carrier_id=seeded_carriers["delhivery"].id,
        carrier_awb="DL-999",
        shipment_type=ShipmentType.FORWARD,
        status=ShipmentStatus.IN_TRANSIT,
        origin_pincode="560001",
        destination_pincode="110001",
        weight_kg=1.0,
        cod_amount=0,
        meta={},
    )
    db_session.add(shipment)
    await db_session.commit()

    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    result = await db_session.execute(
        select(Shipment).options(selectinload(Shipment.tracking_events)).where(Shipment.id == shipment.id)
    )
    shipment = result.scalar_one()

    updated = await tracking_module.sync_shipment_tracking(db_session, shipment, actor="test")

    assert updated.status == ShipmentStatus.DELIVERED
    tracking_module.sync_order_shipment_status.assert_awaited_once()
    tracking_module.notify_shipment_status_change.assert_awaited_once()


@pytest.mark.asyncio
async def test_sync_skips_terminal_shipments(db_session, seeded_carriers, monkeypatch, fake_adapter_factory):
    adapter = fake_adapter_factory("delhivery")
    fetch_mock = AsyncMock(wraps=adapter.fetch_tracking)
    adapter.fetch_tracking = fetch_mock
    monkeypatch.setattr(tracking_module, "get_adapter", lambda code: adapter)

    shipment = Shipment(
        id=uuid.uuid4(),
        order_id=uuid.uuid4(),
        carrier_id=seeded_carriers["delhivery"].id,
        carrier_awb="DL-DONE",
        shipment_type=ShipmentType.FORWARD,
        status=ShipmentStatus.DELIVERED,
        origin_pincode="560001",
        destination_pincode="110001",
        weight_kg=1.0,
        cod_amount=0,
        meta={},
    )
    db_session.add(shipment)
    await db_session.commit()

    await tracking_module.sync_shipment_tracking(db_session, shipment, actor="test")
    fetch_mock.assert_not_awaited()
