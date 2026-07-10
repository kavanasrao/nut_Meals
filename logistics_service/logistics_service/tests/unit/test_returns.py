"""Unit tests for app.services.returns."""
import uuid
from unittest.mock import AsyncMock

import pytest

from app.models.shipment import Shipment, ShipmentStatus, ShipmentType
from app.services import returns as returns_module


@pytest.mark.asyncio
async def test_create_reverse_pickup_success(db_session, seeded_carriers, monkeypatch, fake_adapter_factory):
    adapter = fake_adapter_factory("delhivery", awb="DL-ORIG")
    monkeypatch.setattr(returns_module, "get_adapter", lambda code: adapter)

    original = Shipment(
        id=uuid.uuid4(),
        order_id=uuid.uuid4(),
        carrier_id=seeded_carriers["delhivery"].id,
        carrier_awb="DL-ORIG",
        shipment_type=ShipmentType.FORWARD,
        status=ShipmentStatus.DELIVERED,
        origin_pincode="560001",
        destination_pincode="110001",
        weight_kg=2.0,
        cod_amount=0,
        meta={},
    )
    db_session.add(original)
    await db_session.commit()

    reverse_shipment = await returns_module.create_reverse_pickup(
        db_session,
        original_shipment=original,
        reason="size_mismatch",
        pickup_pincode="110001",
        weight_kg=2.0,
        actor="test-user",
    )

    assert reverse_shipment.shipment_type == ShipmentType.REVERSE
    assert reverse_shipment.carrier_awb == "REV-DL-ORIG"
    assert reverse_shipment.meta["original_shipment_id"] == str(original.id)


@pytest.mark.asyncio
async def test_create_reverse_pickup_fails_without_awb(db_session, seeded_carriers):
    original = Shipment(
        id=uuid.uuid4(),
        order_id=uuid.uuid4(),
        carrier_id=seeded_carriers["delhivery"].id,
        carrier_awb=None,
        shipment_type=ShipmentType.FORWARD,
        status=ShipmentStatus.CREATED,
        origin_pincode="560001",
        destination_pincode="110001",
        weight_kg=1.0,
        cod_amount=0,
        meta={},
    )
    db_session.add(original)
    await db_session.commit()

    with pytest.raises(returns_module.ReversePickupError):
        await returns_module.create_reverse_pickup(
            db_session,
            original_shipment=original,
            reason="damaged",
            pickup_pincode="110001",
            weight_kg=1.0,
            actor="test-user",
        )


@pytest.mark.asyncio
async def test_complete_return_and_restock_notifies_inventory(db_session, seeded_carriers, monkeypatch):
    monkeypatch.setattr(returns_module, "notify_inventory_of_return", AsyncMock(return_value=True))

    reverse_shipment = Shipment(
        id=uuid.uuid4(),
        order_id=uuid.uuid4(),
        carrier_id=seeded_carriers["delhivery"].id,
        carrier_awb="REV-1",
        shipment_type=ShipmentType.REVERSE,
        status=ShipmentStatus.DELIVERED,
        origin_pincode="110001",
        destination_pincode="560001",
        weight_kg=1.0,
        cod_amount=0,
        meta={},
    )
    db_session.add(reverse_shipment)
    await db_session.commit()

    success = await returns_module.complete_return_and_restock(
        db_session, reverse_shipment, sku_items=[{"sku": "NM-001", "qty": 1}], actor="test-user"
    )
    assert success is True
    returns_module.notify_inventory_of_return.assert_awaited_once()
