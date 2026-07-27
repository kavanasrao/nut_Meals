import uuid

import pytest

pytestmark = pytest.mark.integration


async def _setup_approved_po(client, qty=30):
    vendor_resp = await client.post(
        "/api/v1/vendors", json={"name": "GRN Vendor", "email": "grnv@test.com"}
    )
    vendor = vendor_resp.json()

    po_resp = await client.post(
        "/api/v1/purchase-orders",
        json={
            "vendor_id": vendor["id"],
            "items": [
                {"sku": "CASHEW-1KG", "quantity_ordered": qty, "unit_price": "15.00"}
            ],
        },
    )
    po = po_resp.json()

    await client.post(f"/api/v1/purchase-orders/{po['id']}/approval", json={"approve": True})
    po_refreshed = (await client.get(f"/api/v1/purchase-orders/{po['id']}")).json()
    return vendor, po_refreshed


async def test_create_grn_and_fetch_by_id(client):
    vendor, po = await _setup_approved_po(client, qty=30)
    po_item_id = po["items"][0]["id"]

    grn_resp = await client.post(
        "/api/v1/grn",
        json={
            "purchase_order_id": po["id"],
            "remarks": "Received in good condition",
            "items": [
                {
                    "purchase_order_item_id": po_item_id,
                    "sku": "CASHEW-1KG",
                    "quantity_received": 30,
                }
            ],
        },
    )
    assert grn_resp.status_code == 201
    grn = grn_resp.json()

    fetch_resp = await client.get(f"/api/v1/grn/{grn['id']}")
    assert fetch_resp.status_code == 200
    assert fetch_resp.json()["grn_number"] == grn["grn_number"]


async def test_list_grns_for_po(client):
    vendor, po = await _setup_approved_po(client, qty=30)
    po_item_id = po["items"][0]["id"]

    await client.post(
        "/api/v1/grn",
        json={
            "purchase_order_id": po["id"],
            "items": [
                {
                    "purchase_order_item_id": po_item_id,
                    "sku": "CASHEW-1KG",
                    "quantity_received": 10,
                }
            ],
        },
    )
    await client.post(
        "/api/v1/grn",
        json={
            "purchase_order_id": po["id"],
            "items": [
                {
                    "purchase_order_item_id": po_item_id,
                    "sku": "CASHEW-1KG",
                    "quantity_received": 20,
                }
            ],
        },
    )

    list_resp = await client.get(f"/api/v1/grn/by-po/{po['id']}")
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 2


async def test_grn_with_wrong_po_item_rejected(client):
    vendor, po = await _setup_approved_po(client, qty=10)

    resp = await client.post(
        "/api/v1/grn",
        json={
            "purchase_order_id": po["id"],
            "items": [
                {
                    "purchase_order_item_id": str(uuid.uuid4()),
                    "sku": "CASHEW-1KG",
                    "quantity_received": 5,
                }
            ],
        },
    )
    assert resp.status_code == 400


async def test_get_nonexistent_grn_404(client):
    resp = await client.get(f"/api/v1/grn/{uuid.uuid4()}")
    assert resp.status_code == 404
