"""
Unit tests for carrier adapters, using httpx.MockTransport to simulate
carrier API responses without any real network calls.
"""
from datetime import datetime, timezone

import httpx
import pytest

from app.adapters.base import CarrierAPIError
from app.adapters.delhivery import DelhiveryAdapter
from app.adapters.india_post import IndiaPostAdapter


def _client_with_handler(handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="http://carrier.test")


# ---------------------------------------------------------------- Delhivery


@pytest.mark.asyncio
async def test_delhivery_check_serviceability_serviceable():
    def handler(request):
        return httpx.Response(200, json={"delivery_codes": [{"postal_code": {"pin": "560001"}}]})

    adapter = DelhiveryAdapter(client=_client_with_handler(handler))
    result = await adapter.check_serviceability("560001", "110001", 2.0)
    assert result.serviceable is True
    assert result.estimated_cost > 0


@pytest.mark.asyncio
async def test_delhivery_check_serviceability_not_serviceable():
    def handler(request):
        return httpx.Response(200, json={"delivery_codes": []})

    adapter = DelhiveryAdapter(client=_client_with_handler(handler))
    result = await adapter.check_serviceability("560001", "999999", 1.0)
    assert result.serviceable is False


@pytest.mark.asyncio
async def test_delhivery_check_serviceability_http_error_raises_carrier_error():
    def handler(request):
        return httpx.Response(500)

    adapter = DelhiveryAdapter(client=_client_with_handler(handler))
    with pytest.raises(CarrierAPIError):
        await adapter.check_serviceability("560001", "110001", 1.0)


@pytest.mark.asyncio
async def test_delhivery_create_shipment_success():
    def handler(request):
        return httpx.Response(200, json={"packages": [{"waybill": "DLV123", "label_url": "http://x/label.pdf"}]})

    adapter = DelhiveryAdapter(client=_client_with_handler(handler))
    result = await adapter.create_shipment("order-1", "560001", "110001", 1.0, 0)
    assert result.carrier_awb == "DLV123"


@pytest.mark.asyncio
async def test_delhivery_create_shipment_missing_waybill_raises():
    def handler(request):
        return httpx.Response(200, json={"packages": [{}]})

    adapter = DelhiveryAdapter(client=_client_with_handler(handler))
    with pytest.raises(CarrierAPIError):
        await adapter.create_shipment("order-1", "560001", "110001", 1.0, 0)


@pytest.mark.asyncio
async def test_delhivery_create_reverse_pickup_success():
    def handler(request):
        return httpx.Response(200, json={"waybill": "REV-DLV123"})

    adapter = DelhiveryAdapter(client=_client_with_handler(handler))
    result = await adapter.create_reverse_pickup("DLV123", "110001", "damaged", 1.0)
    assert result.carrier_awb == "REV-DLV123"


@pytest.mark.asyncio
async def test_delhivery_fetch_tracking_parses_scans():
    def handler(request):
        return httpx.Response(
            200,
            json={
                "ShipmentData": [
                    {
                        "Shipment": {
                            "Scans": [
                                {
                                    "ScanDetail": {
                                        "Scan": "Delivered",
                                        "StatusDateTime": datetime.now(timezone.utc).isoformat(),
                                        "ScannedLocation": "Bengaluru Hub",
                                        "Instructions": "Delivered to recipient",
                                    }
                                }
                            ]
                        }
                    }
                ]
            },
        )

    adapter = DelhiveryAdapter(client=_client_with_handler(handler))
    updates = await adapter.fetch_tracking("DLV123")
    assert len(updates) == 1
    assert updates[0].status == "delivered"


@pytest.mark.asyncio
async def test_delhivery_fetch_tracking_http_error():
    def handler(request):
        return httpx.Response(503)

    adapter = DelhiveryAdapter(client=_client_with_handler(handler))
    with pytest.raises(CarrierAPIError):
        await adapter.fetch_tracking("DLV123")


# ---------------------------------------------------------------- India Post


@pytest.mark.asyncio
async def test_india_post_check_serviceability_default_true():
    def handler(request):
        return httpx.Response(200, json={})

    adapter = IndiaPostAdapter(client=_client_with_handler(handler))
    result = await adapter.check_serviceability("560001", "110001", 1.0)
    assert result.serviceable is True


@pytest.mark.asyncio
async def test_india_post_check_serviceability_explicit_false():
    def handler(request):
        return httpx.Response(200, json={"serviceable": False})

    adapter = IndiaPostAdapter(client=_client_with_handler(handler))
    result = await adapter.check_serviceability("560001", "000000", 1.0)
    assert result.serviceable is False


@pytest.mark.asyncio
async def test_india_post_check_serviceability_http_error():
    def handler(request):
        return httpx.Response(500)

    adapter = IndiaPostAdapter(client=_client_with_handler(handler))
    with pytest.raises(CarrierAPIError):
        await adapter.check_serviceability("560001", "110001", 1.0)


@pytest.mark.asyncio
async def test_india_post_create_shipment_success():
    def handler(request):
        return httpx.Response(200, json={"consignment_number": "IP999", "label_url": None})

    adapter = IndiaPostAdapter(client=_client_with_handler(handler))
    result = await adapter.create_shipment("order-2", "560001", "110001", 1.0, 100)
    assert result.carrier_awb == "IP999"


@pytest.mark.asyncio
async def test_india_post_create_shipment_missing_consignment_raises():
    def handler(request):
        return httpx.Response(200, json={})

    adapter = IndiaPostAdapter(client=_client_with_handler(handler))
    with pytest.raises(CarrierAPIError):
        await adapter.create_shipment("order-2", "560001", "110001", 1.0, 0)


@pytest.mark.asyncio
async def test_india_post_create_reverse_pickup_success():
    def handler(request):
        return httpx.Response(200, json={"consignment_number": "REV-IP999"})

    adapter = IndiaPostAdapter(client=_client_with_handler(handler))
    result = await adapter.create_reverse_pickup("IP999", "110001", "wrong_size", 1.0)
    assert result.carrier_awb == "REV-IP999"


@pytest.mark.asyncio
async def test_india_post_fetch_tracking_parses_checkpoints():
    def handler(request):
        return httpx.Response(
            200,
            json={
                "checkpoints": [
                    {
                        "status": "delivered",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "office": "Hubballi HO",
                        "description": "Item delivered",
                    }
                ]
            },
        )

    adapter = IndiaPostAdapter(client=_client_with_handler(handler))
    updates = await adapter.fetch_tracking("IP999")
    assert len(updates) == 1
    assert updates[0].status == "delivered"


@pytest.mark.asyncio
async def test_india_post_fetch_tracking_http_error():
    def handler(request):
        return httpx.Response(500)

    adapter = IndiaPostAdapter(client=_client_with_handler(handler))
    with pytest.raises(CarrierAPIError):
        await adapter.fetch_tracking("IP999")
