"""Unit tests for services.order_client and services.notification (mocked HTTP)."""
import httpx
import pytest

from app.services import notification as notification_module
from app.services import order_client as order_client_module


@pytest.mark.asyncio
async def test_sync_order_shipment_status_success(monkeypatch):
    def handler(request):
        return httpx.Response(200, json={"ok": True})

    class FakeAsyncClient(httpx.AsyncClient):
        def __init__(self, *args, **kwargs):
            kwargs["transport"] = httpx.MockTransport(handler)
            super().__init__(*args, **kwargs)

    monkeypatch.setattr(order_client_module.httpx, "AsyncClient", FakeAsyncClient)
    ok = await order_client_module.sync_order_shipment_status("order-1", "delivered", "AWB1")
    assert ok is True


@pytest.mark.asyncio
async def test_sync_order_shipment_status_failure(monkeypatch):
    def handler(request):
        return httpx.Response(500)

    class FakeAsyncClient(httpx.AsyncClient):
        def __init__(self, *args, **kwargs):
            kwargs["transport"] = httpx.MockTransport(handler)
            super().__init__(*args, **kwargs)

    monkeypatch.setattr(order_client_module.httpx, "AsyncClient", FakeAsyncClient)
    ok = await order_client_module.sync_order_shipment_status("order-1", "delivered", "AWB1")
    assert ok is False


@pytest.mark.asyncio
async def test_notify_inventory_of_return_success(monkeypatch):
    def handler(request):
        return httpx.Response(200, json={"ok": True})

    class FakeAsyncClient(httpx.AsyncClient):
        def __init__(self, *args, **kwargs):
            kwargs["transport"] = httpx.MockTransport(handler)
            super().__init__(*args, **kwargs)

    monkeypatch.setattr(order_client_module.httpx, "AsyncClient", FakeAsyncClient)
    ok = await order_client_module.notify_inventory_of_return("order-1", [{"sku": "NM-1", "qty": 1}])
    assert ok is True


@pytest.mark.asyncio
async def test_notify_shipment_status_change_logs_but_does_not_raise(monkeypatch):
    def handler(request):
        return httpx.Response(500)

    class FakeAsyncClient(httpx.AsyncClient):
        def __init__(self, *args, **kwargs):
            kwargs["transport"] = httpx.MockTransport(handler)
            super().__init__(*args, **kwargs)

    monkeypatch.setattr(notification_module.httpx, "AsyncClient", FakeAsyncClient)
    # Should not raise even though the messaging service call fails.
    await notification_module.notify_shipment_status_change("order-1", "delivered", "AWB1")


@pytest.mark.asyncio
async def test_notify_shipment_status_change_success(monkeypatch):
    def handler(request):
        return httpx.Response(200, json={"queued": True})

    class FakeAsyncClient(httpx.AsyncClient):
        def __init__(self, *args, **kwargs):
            kwargs["transport"] = httpx.MockTransport(handler)
            super().__init__(*args, **kwargs)

    monkeypatch.setattr(notification_module.httpx, "AsyncClient", FakeAsyncClient)
    await notification_module.notify_shipment_status_change("order-1", "delivered", "AWB1")
