"""Tests for inventory reservation create/confirm/release flows."""
import pytest

pytestmark = pytest.mark.asyncio


async def test_create_reservation_holds_stock(client, admin_headers, orders_service_headers, seeded_warehouse, seeded_items):
    await client.post(
        f"/api/v1/warehouses/{seeded_warehouse.id}/stock/adjust",
        json={"item_id": str(seeded_items["bar"].id), "quantity_delta": 20},
        headers=admin_headers,
    )
    resp = await client.post(
        "/api/v1/reservations",
        json={
            "order_id": "ORDER-1", "item_id": str(seeded_items["bar"].id),
            "warehouse_id": str(seeded_warehouse.id), "quantity": 5,
        },
        headers=orders_service_headers,
    )
    assert resp.status_code == 201
    assert resp.json()["status"] == "active"

    stock = await client.get(f"/api/v1/warehouses/{seeded_warehouse.id}/stock", headers=admin_headers)
    bar_stock = next(s for s in stock.json() if s["item_id"] == str(seeded_items["bar"].id))
    assert bar_stock["quantity_reserved"] == 5
    assert bar_stock["quantity_on_hand"] == 20  # unchanged until confirmed


async def test_reservation_insufficient_stock_rejected(client, orders_service_headers, seeded_warehouse, seeded_items):
    resp = await client.post(
        "/api/v1/reservations",
        json={
            "order_id": "ORDER-2", "item_id": str(seeded_items["bar"].id),
            "warehouse_id": str(seeded_warehouse.id), "quantity": 999,
        },
        headers=orders_service_headers,
    )
    assert resp.status_code == 400


async def test_confirm_reservation_deducts_stock(client, admin_headers, orders_service_headers, seeded_warehouse, seeded_items):
    await client.post(
        f"/api/v1/warehouses/{seeded_warehouse.id}/stock/adjust",
        json={"item_id": str(seeded_items["bar"].id), "quantity_delta": 20},
        headers=admin_headers,
    )
    reserve_resp = await client.post(
        "/api/v1/reservations",
        json={
            "order_id": "ORDER-3", "item_id": str(seeded_items["bar"].id),
            "warehouse_id": str(seeded_warehouse.id), "quantity": 5,
        },
        headers=orders_service_headers,
    )
    reservation_id = reserve_resp.json()["id"]

    confirm_resp = await client.post(f"/api/v1/reservations/{reservation_id}/confirm", headers=orders_service_headers)
    assert confirm_resp.status_code == 200
    assert confirm_resp.json()["status"] == "confirmed"

    stock = await client.get(f"/api/v1/warehouses/{seeded_warehouse.id}/stock", headers=admin_headers)
    bar_stock = next(s for s in stock.json() if s["item_id"] == str(seeded_items["bar"].id))
    assert bar_stock["quantity_on_hand"] == 15
    assert bar_stock["quantity_reserved"] == 0


async def test_release_reservation_returns_stock(client, admin_headers, orders_service_headers, seeded_warehouse, seeded_items):
    await client.post(
        f"/api/v1/warehouses/{seeded_warehouse.id}/stock/adjust",
        json={"item_id": str(seeded_items["bar"].id), "quantity_delta": 20},
        headers=admin_headers,
    )
    reserve_resp = await client.post(
        "/api/v1/reservations",
        json={
            "order_id": "ORDER-4", "item_id": str(seeded_items["bar"].id),
            "warehouse_id": str(seeded_warehouse.id), "quantity": 5,
        },
        headers=orders_service_headers,
    )
    reservation_id = reserve_resp.json()["id"]

    release_resp = await client.post(f"/api/v1/reservations/{reservation_id}/release", headers=orders_service_headers)
    assert release_resp.status_code == 200
    assert release_resp.json()["status"] == "released"

    stock = await client.get(f"/api/v1/warehouses/{seeded_warehouse.id}/stock", headers=admin_headers)
    bar_stock = next(s for s in stock.json() if s["item_id"] == str(seeded_items["bar"].id))
    assert bar_stock["quantity_reserved"] == 0
    assert bar_stock["quantity_on_hand"] == 20


async def test_release_is_idempotent(client, admin_headers, orders_service_headers, seeded_warehouse, seeded_items):
    await client.post(
        f"/api/v1/warehouses/{seeded_warehouse.id}/stock/adjust",
        json={"item_id": str(seeded_items["bar"].id), "quantity_delta": 20},
        headers=admin_headers,
    )
    reserve_resp = await client.post(
        "/api/v1/reservations",
        json={
            "order_id": "ORDER-5", "item_id": str(seeded_items["bar"].id),
            "warehouse_id": str(seeded_warehouse.id), "quantity": 5,
        },
        headers=orders_service_headers,
    )
    reservation_id = reserve_resp.json()["id"]
    await client.post(f"/api/v1/reservations/{reservation_id}/release", headers=orders_service_headers)
    second_release = await client.post(f"/api/v1/reservations/{reservation_id}/release", headers=orders_service_headers)
    assert second_release.status_code == 200
    assert second_release.json()["status"] == "released"


async def test_orders_service_role_scoped_to_reservations_only(client, orders_service_headers):
    """The service-to-service token should not grant warehouse admin rights."""
    resp = await client.post(
        "/api/v1/warehouses",
        json={"code": "WH-X", "name": "X", "location": "Y", "capacity_units": 100},
        headers=orders_service_headers,
    )
    assert resp.status_code == 403
