"""
Registry mapping CarrierCode -> adapter instance.

Adding a new carrier requires: (1) a new adapter module implementing
BaseCarrierAdapter, (2) one line here, (3) a `Carrier` row in the DB via
migration/seed. No other code needs to change.
"""
from app.adapters.base import BaseCarrierAdapter
from app.adapters.delhivery import DelhiveryAdapter
from app.adapters.india_post import IndiaPostAdapter
from app.models.carrier import CarrierCode

_REGISTRY: dict[CarrierCode, type[BaseCarrierAdapter]] = {
    CarrierCode.DELHIVERY: DelhiveryAdapter,
    CarrierCode.INDIA_POST: IndiaPostAdapter,
}

_instances: dict[CarrierCode, BaseCarrierAdapter] = {}


def get_adapter(code: CarrierCode) -> BaseCarrierAdapter:
    """Return a (cached) adapter instance for the given carrier code."""
    if code not in _instances:
        adapter_cls = _REGISTRY.get(code)
        if adapter_cls is None:
            raise ValueError(f"No adapter registered for carrier code: {code}")
        _instances[code] = adapter_cls()
    return _instances[code]


def all_carrier_codes() -> list[CarrierCode]:
    return list(_REGISTRY.keys())
