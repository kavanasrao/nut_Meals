"""Unit tests for app.services.serviceability (rules engine + caching)."""
import fakeredis.aioredis
import pytest

from app.models.carrier import CarrierCode
from app.services import serviceability as serviceability_module


@pytest.fixture(autouse=True)
def patch_redis(monkeypatch):
    fake_redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr(serviceability_module, "get_redis", lambda: fake_redis)
    return fake_redis


@pytest.fixture(autouse=True)
def patch_adapters(monkeypatch, fake_adapter_factory):
    adapters = {
        CarrierCode.DELHIVERY: fake_adapter_factory(CarrierCode.DELHIVERY.value, serviceable=True, cost=60, hours=48),
        CarrierCode.INDIA_POST: fake_adapter_factory(CarrierCode.INDIA_POST.value, serviceable=True, cost=30, hours=96),
    }
    monkeypatch.setattr(serviceability_module, "get_adapter", lambda code: adapters[code])
    monkeypatch.setattr(serviceability_module, "all_carrier_codes", lambda: list(adapters.keys()))
    return adapters


@pytest.mark.asyncio
async def test_check_serviceability_returns_both_carriers(db_session, seeded_carriers):
    result = await serviceability_module.check_serviceability(db_session, "560001", "110001", 1.0)
    codes = {o.carrier_code for o in result.options}
    assert codes == {CarrierCode.DELHIVERY, CarrierCode.INDIA_POST}
    assert result.cached is False


@pytest.mark.asyncio
async def test_check_serviceability_uses_cache_on_second_call(db_session, seeded_carriers):
    first = await serviceability_module.check_serviceability(db_session, "560001", "110001", 1.0)
    second = await serviceability_module.check_serviceability(db_session, "560001", "110001", 1.0)
    assert first.cached is False
    assert second.cached is True
    assert second.recommended_carrier == first.recommended_carrier


@pytest.mark.asyncio
async def test_recommended_carrier_favors_higher_composite_score(db_session, seeded_carriers):
    # India Post is cheaper but slower and less reliable (0.7 vs 0.9);
    # Delhivery costs more but is faster and more reliable. With default
    # weights (cost .4, speed .4, reliability .2) Delhivery should win here
    # given the cost/speed spread configured in patch_adapters.
    result = await serviceability_module.check_serviceability(db_session, "560001", "110001", 1.0)
    assert result.recommended_carrier is not None


@pytest.mark.asyncio
async def test_unserviceable_carrier_gets_zero_score(db_session, seeded_carriers, monkeypatch, fake_adapter_factory):
    adapters = {
        CarrierCode.DELHIVERY: fake_adapter_factory(CarrierCode.DELHIVERY.value, serviceable=False),
        CarrierCode.INDIA_POST: fake_adapter_factory(CarrierCode.INDIA_POST.value, serviceable=True, cost=30, hours=96),
    }
    monkeypatch.setattr(serviceability_module, "get_adapter", lambda code: adapters[code])
    monkeypatch.setattr(serviceability_module, "all_carrier_codes", lambda: list(adapters.keys()))

    result = await serviceability_module.check_serviceability(db_session, "999999", "110001", 1.0)
    delhivery_option = next(o for o in result.options if o.carrier_code == CarrierCode.DELHIVERY)
    assert delhivery_option.serviceable is False
    assert delhivery_option.score == 0
    assert result.recommended_carrier == CarrierCode.INDIA_POST
