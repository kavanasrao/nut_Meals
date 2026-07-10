"""Unit tests for app.services.allocation (carrier selection + fallback)."""
import uuid

import fakeredis.aioredis
import pytest

from app.models.carrier import CarrierCode
from app.models.shipment import ShipmentStatus
from app.services import allocation as allocation_module
from app.services import serviceability as serviceability_module


@pytest.fixture(autouse=True)
def patch_redis(monkeypatch):
    fake_redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr(serviceability_module, "get_redis", lambda: fake_redis)
    return fake_redis


@pytest.mark.asyncio
async def test_allocate_books_recommended_carrier(db_session, seeded_carriers, monkeypatch, fake_adapter_factory):
    adapters = {
        CarrierCode.DELHIVERY: fake_adapter_factory(CarrierCode.DELHIVERY.value, cost=40, hours=48, awb="DL-001"),
        CarrierCode.INDIA_POST: fake_adapter_factory(CarrierCode.INDIA_POST.value, cost=60, hours=96, awb="IP-001"),
    }
    monkeypatch.setattr(allocation_module, "get_adapter", lambda code: adapters[code])
    monkeypatch.setattr(serviceability_module, "get_adapter", lambda code: adapters[code])
    monkeypatch.setattr(serviceability_module, "all_carrier_codes", lambda: list(adapters.keys()))

    shipment = await allocation_module.allocate_and_book_shipment(
        db_session,
        order_id=uuid.uuid4(),
        origin_pincode="560001",
        destination_pincode="110001",
        weight_kg=1.0,
        cod_amount=0,
        actor="test-user",
    )
    assert shipment.status == ShipmentStatus.CREATED
    assert shipment.carrier_awb == "DL-001"


@pytest.mark.asyncio
async def test_allocate_falls_back_when_primary_carrier_booking_fails(
    db_session, seeded_carriers, monkeypatch, fake_adapter_factory
):
    adapters = {
        CarrierCode.DELHIVERY: fake_adapter_factory(
            CarrierCode.DELHIVERY.value, cost=40, hours=48, booking_should_fail=True
        ),
        CarrierCode.INDIA_POST: fake_adapter_factory(CarrierCode.INDIA_POST.value, cost=60, hours=96, awb="IP-FALLBACK"),
    }
    monkeypatch.setattr(allocation_module, "get_adapter", lambda code: adapters[code])
    monkeypatch.setattr(serviceability_module, "get_adapter", lambda code: adapters[code])
    monkeypatch.setattr(serviceability_module, "all_carrier_codes", lambda: list(adapters.keys()))

    shipment = await allocation_module.allocate_and_book_shipment(
        db_session,
        order_id=uuid.uuid4(),
        origin_pincode="560001",
        destination_pincode="110001",
        weight_kg=1.0,
        cod_amount=0,
        actor="test-user",
    )
    # Delhivery (higher score, cheaper+faster) fails -> should fall back to India Post
    assert shipment.carrier_awb == "IP-FALLBACK"


@pytest.mark.asyncio
async def test_allocate_raises_when_no_carrier_serviceable(
    db_session, seeded_carriers, monkeypatch, fake_adapter_factory
):
    adapters = {
        CarrierCode.DELHIVERY: fake_adapter_factory(CarrierCode.DELHIVERY.value, serviceable=False),
        CarrierCode.INDIA_POST: fake_adapter_factory(CarrierCode.INDIA_POST.value, serviceable=False),
    }
    monkeypatch.setattr(allocation_module, "get_adapter", lambda code: adapters[code])
    monkeypatch.setattr(serviceability_module, "get_adapter", lambda code: adapters[code])
    monkeypatch.setattr(serviceability_module, "all_carrier_codes", lambda: list(adapters.keys()))

    with pytest.raises(allocation_module.NoServiceableCarrierError):
        await allocation_module.allocate_and_book_shipment(
            db_session,
            order_id=uuid.uuid4(),
            origin_pincode="999999",
            destination_pincode="999999",
            weight_kg=1.0,
            cod_amount=0,
            actor="test-user",
        )
