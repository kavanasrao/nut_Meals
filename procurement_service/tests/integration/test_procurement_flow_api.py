import pytest

pytestmark = pytest.mark.integration


async def _create_vendor(client, name="Flow Vendor", email="flow@test.com"):
    resp = await client.post("/api/v1/vendors", json={"name": name, "email": email})
    assert resp.status_code == 201
    return resp.json()


async def test_full_procurement_lifecycle(client):
    # 1. Create vendor
    vendor = await _create_vendor(client)

    # 2. Create PO
    po_resp = await client.post(
        "/api/v1/purchase-orders",
        json={
            "vendor_id": vendor["id"],
            "items": [
                {
                    "sku": "ALMOND-500G",
                    "description": "Almonds 500g pack",
                    "quantity_ordered": 100,
                    "unit_price": "20.00",
                    "tax_rate_percent": "5",
                }
            ],
        },
    )
    assert po_resp.status_code == 201
    po = po_resp.json()
    assert po["status"] == "pending_approval"
    assert po["total_amount"] == "2100.00"

    # 3. Approve PO
    approve_resp = await client.post(
        f"/api/v1/purchase-orders/{po['id']}/approval", json={"approve": True}
    )
    assert approve_resp.status_code == 200
    assert approve_resp.json()["status"] == "approved"

    # 4. Record GRN (partial receipt)
    po_item_id = po["items"][0]["id"]
    grn_resp = await client.post(
        "/api/v1/grn",
        json={
            "purchase_order_id": po["id"],
            "items": [
                {
                    "purchase_order_item_id": po_item_id,
                    "sku": "ALMOND-500G",
                    "quantity_received": 100,
                }
            ],
        },
    )
    assert grn_resp.status_code == 201
    grn = grn_resp.json()
    assert grn["status"] == "confirmed"

    po_after_grn = await client.get(f"/api/v1/purchase-orders/{po['id']}")
    assert po_after_grn.json()["status"] == "received"

    # 5. Book invoice referencing PO + GRN
    invoice_resp = await client.post(
        "/api/v1/invoices",
        json={
            "invoice_number": "INV-FLOW-001",
            "vendor_id": vendor["id"],
            "purchase_order_id": po["id"],
            "grn_id": grn["id"],
            "invoice_date": "2026-07-20",
            "items": [
                {
                    "sku": "ALMOND-500G",
                    "quantity": 100,
                    "unit_price": "20.00",
                    "tax_rate_percent": "5",
                }
            ],
        },
    )
    assert invoice_resp.status_code == 201
    invoice = invoice_resp.json()
    assert invoice["total_amount"] == "2100.00"
    assert invoice["status"] == "received"

    # 6. Trigger 3-way match
    match_resp = await client.post(f"/api/v1/invoices/{invoice['id']}/match")
    assert match_resp.status_code == 200
    assert match_resp.json()["status"] == "matched"

    # 7. Vendor ledger reflects the invoice as a payable
    ledger_resp = await client.get(f"/api/v1/vendors/{vendor['id']}/ledger")
    assert ledger_resp.status_code == 200
    assert ledger_resp.json()["current_balance"] == "-2100.00"


async def test_po_rejection_flow(client):
    vendor = await _create_vendor(client, name="Reject Vendor", email="reject@test.com")
    po_resp = await client.post(
        "/api/v1/purchase-orders",
        json={
            "vendor_id": vendor["id"],
            "items": [
                {"sku": "SKU-R", "quantity_ordered": 5, "unit_price": "10.00"}
            ],
        },
    )
    po = po_resp.json()

    reject_resp = await client.post(
        f"/api/v1/purchase-orders/{po['id']}/approval",
        json={"approve": False, "rejection_reason": "Price too high"},
    )
    assert reject_resp.status_code == 200
    body = reject_resp.json()
    assert body["status"] == "rejected"
    assert body["rejection_reason"] == "Price too high"


async def test_cannot_receive_against_pending_po(client):
    vendor = await _create_vendor(client, name="Pending Vendor", email="pending@test.com")
    po_resp = await client.post(
        "/api/v1/purchase-orders",
        json={
            "vendor_id": vendor["id"],
            "items": [{"sku": "SKU-P", "quantity_ordered": 5, "unit_price": "10.00"}],
        },
    )
    po = po_resp.json()
    po_item_id = po["items"][0]["id"]

    grn_resp = await client.post(
        "/api/v1/grn",
        json={
            "purchase_order_id": po["id"],
            "items": [
                {"purchase_order_item_id": po_item_id, "sku": "SKU-P", "quantity_received": 1}
            ],
        },
    )
    assert grn_resp.status_code == 409
