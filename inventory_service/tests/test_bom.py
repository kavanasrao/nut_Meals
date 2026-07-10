"""Tests for Bill of Materials: creation, versioning, availability validation."""
import pytest

pytestmark = pytest.mark.asyncio


async def _create_bom(client, headers, product_id, component_id, qty=2.0, yield_qty=1.0):
    return await client.post(
        "/api/v1/bom",
        json={
            "product_item_id": str(product_id),
            "yield_quantity": yield_qty,
            "components": [{"component_item_id": str(component_id), "quantity_required": qty}],
        },
        headers=headers,
    )


async def test_create_bom(client, admin_headers, seeded_items):
    resp = await _create_bom(client, admin_headers, seeded_items["bar"].id, seeded_items["almonds"].id)
    assert resp.status_code == 201
    body = resp.json()
    assert body["version"] == 1
    assert body["is_active"] is True
    assert len(body["components"]) == 1


async def test_bom_versioning_supersedes_previous(client, admin_headers, seeded_items):
    r1 = await _create_bom(client, admin_headers, seeded_items["bar"].id, seeded_items["almonds"].id)
    r2 = await _create_bom(client, admin_headers, seeded_items["bar"].id, seeded_items["almonds"].id, qty=3.0)
    assert r1.json()["version"] == 1
    assert r2.json()["version"] == 2

    active = await client.get(
        f"/api/v1/bom/product/{seeded_items['bar'].id}/active", headers=admin_headers
    )
    assert active.json()["version"] == 2

    versions = await client.get(
        f"/api/v1/bom/product/{seeded_items['bar'].id}/versions", headers=admin_headers
    )
    assert len(versions.json()) == 2


async def test_availability_check_sufficient_stock(client, admin_headers, seeded_warehouse, seeded_items):
    await client.post(
        f"/api/v1/warehouses/{seeded_warehouse.id}/stock/adjust",
        json={"item_id": str(seeded_items["almonds"].id), "quantity_delta": 100},
        headers=admin_headers,
    )
    bom_resp = await _create_bom(client, admin_headers, seeded_items["bar"].id, seeded_items["almonds"].id, qty=2.0)
    bom_id = bom_resp.json()["id"]

    resp = await client.post(
        f"/api/v1/bom/{bom_id}/check-availability",
        json={"warehouse_id": str(seeded_warehouse.id), "planned_quantity": 10},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["is_available"] is True


async def test_availability_check_insufficient_stock(client, admin_headers, seeded_warehouse, seeded_items):
    await client.post(
        f"/api/v1/warehouses/{seeded_warehouse.id}/stock/adjust",
        json={"item_id": str(seeded_items["almonds"].id), "quantity_delta": 5},
        headers=admin_headers,
    )
    bom_resp = await _create_bom(client, admin_headers, seeded_items["bar"].id, seeded_items["almonds"].id, qty=2.0)
    bom_id = bom_resp.json()["id"]

    resp = await client.post(
        f"/api/v1/bom/{bom_id}/check-availability",
        json={"warehouse_id": str(seeded_warehouse.id), "planned_quantity": 10},
        headers=admin_headers,
    )
    body = resp.json()
    assert body["is_available"] is False
    assert len(body["shortfalls"]) == 1
