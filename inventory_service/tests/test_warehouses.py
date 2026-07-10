"""Tests for warehouse CRUD, stock adjustments, and transfers."""
import pytest

pytestmark = pytest.mark.asyncio


async def test_create_warehouse(client, admin_headers):
    resp = await client.post(
        "/api/v1/warehouses",
        json={"code": "WH-01", "name": "Primary", "location": "Austin, TX", "capacity_units": 5000},
        headers=admin_headers,
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["code"] == "WH-01"
    assert body["is_active"] is True


async def test_create_warehouse_duplicate_code_conflicts(client, admin_headers):
    payload = {"code": "WH-DUP", "name": "A", "location": "X", "capacity_units": 100}
    r1 = await client.post("/api/v1/warehouses", json=payload, headers=admin_headers)
    assert r1.status_code == 201
    r2 = await client.post("/api/v1/warehouses", json=payload, headers=admin_headers)
    assert r2.status_code == 409


async def test_create_warehouse_requires_auth(client):
    resp = await client.post(
        "/api/v1/warehouses",
        json={"code": "WH-02", "name": "X", "location": "Y", "capacity_units": 100},
    )
    assert resp.status_code == 401


async def test_viewer_cannot_create_warehouse(client, viewer_headers):
    resp = await client.post(
        "/api/v1/warehouses",
        json={"code": "WH-03", "name": "X", "location": "Y", "capacity_units": 100},
        headers=viewer_headers,
    )
    assert resp.status_code == 403


async def test_stock_adjustment_increases_on_hand(client, admin_headers, seeded_warehouse, seeded_items):
    resp = await client.post(
        f"/api/v1/warehouses/{seeded_warehouse.id}/stock/adjust",
        json={"item_id": str(seeded_items["almonds"].id), "quantity_delta": 50, "lot_number": "LOT-1"},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["quantity_on_hand"] == 50
    assert body["quantity_reserved"] == 0


async def test_stock_adjustment_cannot_go_below_reserved(client, admin_headers, seeded_warehouse, seeded_items):
    await client.post(
        f"/api/v1/warehouses/{seeded_warehouse.id}/stock/adjust",
        json={"item_id": str(seeded_items["almonds"].id), "quantity_delta": 10},
        headers=admin_headers,
    )
    resp = await client.post(
        f"/api/v1/warehouses/{seeded_warehouse.id}/stock/adjust",
        json={"item_id": str(seeded_items["almonds"].id), "quantity_delta": -100},
        headers=admin_headers,
    )
    assert resp.status_code == 400


async def test_transfer_between_warehouses(
    client, admin_headers, seeded_warehouse, seeded_second_warehouse, seeded_items
):
    await client.post(
        f"/api/v1/warehouses/{seeded_warehouse.id}/stock/adjust",
        json={"item_id": str(seeded_items["almonds"].id), "quantity_delta": 100},
        headers=admin_headers,
    )
    resp = await client.post(
        "/api/v1/warehouses/transfers",
        json={
            "item_id": str(seeded_items["almonds"].id),
            "source_warehouse_id": str(seeded_warehouse.id),
            "destination_warehouse_id": str(seeded_second_warehouse.id),
            "quantity": 30,
        },
        headers=admin_headers,
    )
    assert resp.status_code == 201

    source_stock = await client.get(f"/api/v1/warehouses/{seeded_warehouse.id}/stock", headers=admin_headers)
    dest_stock = await client.get(f"/api/v1/warehouses/{seeded_second_warehouse.id}/stock", headers=admin_headers)
    assert source_stock.json()[0]["quantity_on_hand"] == 70
    assert dest_stock.json()[0]["quantity_on_hand"] == 30


async def test_transfer_insufficient_stock_fails(
    client, admin_headers, seeded_warehouse, seeded_second_warehouse, seeded_items
):
    resp = await client.post(
        "/api/v1/warehouses/transfers",
        json={
            "item_id": str(seeded_items["almonds"].id),
            "source_warehouse_id": str(seeded_warehouse.id),
            "destination_warehouse_id": str(seeded_second_warehouse.id),
            "quantity": 999,
        },
        headers=admin_headers,
    )
    assert resp.status_code == 400


async def test_transfer_same_warehouse_rejected(client, admin_headers, seeded_warehouse, seeded_items):
    resp = await client.post(
        "/api/v1/warehouses/transfers",
        json={
            "item_id": str(seeded_items["almonds"].id),
            "source_warehouse_id": str(seeded_warehouse.id),
            "destination_warehouse_id": str(seeded_warehouse.id),
            "quantity": 1,
        },
        headers=admin_headers,
    )
    assert resp.status_code == 400
