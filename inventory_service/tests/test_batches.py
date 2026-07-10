"""Tests for production batch creation, status transitions, and inventory updates."""
import pytest

pytestmark = pytest.mark.asyncio


async def _setup_bom_with_stock(client, admin_headers, seeded_warehouse, seeded_items, component_qty=2.0, stock=100):
    await client.post(
        f"/api/v1/warehouses/{seeded_warehouse.id}/stock/adjust",
        json={"item_id": str(seeded_items["almonds"].id), "quantity_delta": stock},
        headers=admin_headers,
    )
    bom_resp = await client.post(
        "/api/v1/bom",
        json={
            "product_item_id": str(seeded_items["bar"].id),
            "yield_quantity": 1.0,
            "components": [{"component_item_id": str(seeded_items["almonds"].id), "quantity_required": component_qty}],
        },
        headers=admin_headers,
    )
    return bom_resp.json()["id"]


async def test_create_batch_success(client, admin_headers, seeded_warehouse, seeded_items):
    bom_id = await _setup_bom_with_stock(client, admin_headers, seeded_warehouse, seeded_items)
    resp = await client.post(
        "/api/v1/batches",
        json={
            "bom_id": bom_id, "warehouse_id": str(seeded_warehouse.id),
            "planned_quantity": 10, "lot_number": "LOT-BATCH-1",
        },
        headers=admin_headers,
    )
    assert resp.status_code == 201
    assert resp.json()["status"] == "planned"


async def test_create_batch_insufficient_stock_rejected(client, admin_headers, seeded_warehouse, seeded_items):
    bom_id = await _setup_bom_with_stock(client, admin_headers, seeded_warehouse, seeded_items, stock=1)
    resp = await client.post(
        "/api/v1/batches",
        json={
            "bom_id": bom_id, "warehouse_id": str(seeded_warehouse.id),
            "planned_quantity": 100, "lot_number": "LOT-BATCH-2",
        },
        headers=admin_headers,
    )
    assert resp.status_code == 400


async def test_batch_full_lifecycle_updates_inventory(client, admin_headers, seeded_warehouse, seeded_items):
    bom_id = await _setup_bom_with_stock(client, admin_headers, seeded_warehouse, seeded_items, component_qty=2.0, stock=100)
    create_resp = await client.post(
        "/api/v1/batches",
        json={
            "bom_id": bom_id, "warehouse_id": str(seeded_warehouse.id),
            "planned_quantity": 10, "lot_number": "LOT-BATCH-3",
        },
        headers=admin_headers,
    )
    batch_id = create_resp.json()["id"]

    start_resp = await client.post(f"/api/v1/batches/{batch_id}/start", headers=admin_headers)
    assert start_resp.status_code == 200
    assert start_resp.json()["status"] == "in_progress"

    almond_stock = await client.get(f"/api/v1/warehouses/{seeded_warehouse.id}/stock", headers=admin_headers)
    almond_level = next(s for s in almond_stock.json() if s["item_id"] == str(seeded_items["almonds"].id))
    assert almond_level["quantity_on_hand"] == 80  # 100 - (2 * 10)

    complete_resp = await client.post(
        f"/api/v1/batches/{batch_id}/status",
        json={"status": "completed", "actual_yield_quantity": 9.5},
        headers=admin_headers,
    )
    assert complete_resp.status_code == 200
    assert complete_resp.json()["status"] == "completed"

    bar_stock = await client.get(f"/api/v1/warehouses/{seeded_warehouse.id}/stock", headers=admin_headers)
    bar_level = next(s for s in bar_stock.json() if s["item_id"] == str(seeded_items["bar"].id))
    assert bar_level["quantity_on_hand"] == 9.5


async def test_invalid_status_transition_rejected(client, admin_headers, seeded_warehouse, seeded_items):
    bom_id = await _setup_bom_with_stock(client, admin_headers, seeded_warehouse, seeded_items)
    create_resp = await client.post(
        "/api/v1/batches",
        json={
            "bom_id": bom_id, "warehouse_id": str(seeded_warehouse.id),
            "planned_quantity": 10, "lot_number": "LOT-BATCH-4",
        },
        headers=admin_headers,
    )
    batch_id = create_resp.json()["id"]

    # Cannot complete a batch that hasn't started (PLANNED -> COMPLETED invalid)
    resp = await client.post(
        f"/api/v1/batches/{batch_id}/status",
        json={"status": "completed", "actual_yield_quantity": 5},
        headers=admin_headers,
    )
    assert resp.status_code == 400


async def test_complete_batch_requires_yield_quantity(client, admin_headers, seeded_warehouse, seeded_items):
    bom_id = await _setup_bom_with_stock(client, admin_headers, seeded_warehouse, seeded_items)
    create_resp = await client.post(
        "/api/v1/batches",
        json={
            "bom_id": bom_id, "warehouse_id": str(seeded_warehouse.id),
            "planned_quantity": 10, "lot_number": "LOT-BATCH-5",
        },
        headers=admin_headers,
    )
    batch_id = create_resp.json()["id"]
    await client.post(f"/api/v1/batches/{batch_id}/start", headers=admin_headers)

    resp = await client.post(
        f"/api/v1/batches/{batch_id}/status", json={"status": "completed"}, headers=admin_headers
    )
    assert resp.status_code == 400
