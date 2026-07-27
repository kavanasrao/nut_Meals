import uuid

import pytest

pytestmark = pytest.mark.integration


async def test_create_invoice_without_po(client):
    vendor_resp = await client.post(
        "/api/v1/vendors", json={"name": "Standalone Invoice Vendor", "email": "siv@test.com"}
    )
    vendor = vendor_resp.json()

    resp = await client.post(
        "/api/v1/invoices",
        json={
            "invoice_number": "INV-STANDALONE-1",
            "vendor_id": vendor["id"],
            "invoice_date": "2026-07-20",
            "items": [
                {"sku": "MISC-ITEM", "quantity": 3, "unit_price": "9.99", "tax_rate_percent": "0"}
            ],
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "received"
    assert body["total_amount"] == "29.97"


async def test_update_invoice_status(client):
    vendor_resp = await client.post(
        "/api/v1/vendors", json={"name": "Status Vendor", "email": "sv@test.com"}
    )
    vendor = vendor_resp.json()

    invoice_resp = await client.post(
        "/api/v1/invoices",
        json={
            "invoice_number": "INV-STATUS-1",
            "vendor_id": vendor["id"],
            "invoice_date": "2026-07-20",
            "items": [{"sku": "A", "quantity": 1, "unit_price": "10.00"}],
        },
    )
    invoice = invoice_resp.json()

    patch_resp = await client.patch(
        f"/api/v1/invoices/{invoice['id']}/status",
        json={"status": "approved_for_payment", "reconciliation_notes": "Manually approved"},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["status"] == "approved_for_payment"


async def test_list_invoices_filter_by_vendor(client):
    vendor_a = (
        await client.post("/api/v1/vendors", json={"name": "Vendor A", "email": "a@test.com"})
    ).json()
    vendor_b = (
        await client.post("/api/v1/vendors", json={"name": "Vendor B", "email": "b@test.com"})
    ).json()

    for vendor, num in [(vendor_a, "INV-A-1"), (vendor_b, "INV-B-1")]:
        await client.post(
            "/api/v1/invoices",
            json={
                "invoice_number": num,
                "vendor_id": vendor["id"],
                "invoice_date": "2026-07-20",
                "items": [{"sku": "X", "quantity": 1, "unit_price": "5.00"}],
            },
        )

    resp = await client.get("/api/v1/invoices", params={"vendor_id": vendor_a["id"]})
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["vendor_id"] == vendor_a["id"]


async def test_get_nonexistent_invoice_404(client):
    resp = await client.get(f"/api/v1/invoices/{uuid.uuid4()}")
    assert resp.status_code == 404


async def test_invoice_for_nonexistent_vendor_404(client):
    resp = await client.post(
        "/api/v1/invoices",
        json={
            "invoice_number": "INV-BAD-VENDOR",
            "vendor_id": str(uuid.uuid4()),
            "invoice_date": "2026-07-20",
            "items": [{"sku": "A", "quantity": 1, "unit_price": "10.00"}],
        },
    )
    assert resp.status_code == 404
