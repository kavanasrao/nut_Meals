"""Integration tests for one-click login checkout endpoints."""
import uuid

import pytest

from app.models.one_click import SavedAddress, SavedPaymentMethod

pytestmark = pytest.mark.asyncio


async def _seed_address_and_payment(db_session, customer_id: str):
    address = SavedAddress(
        customer_id=uuid.UUID(customer_id),
        label="Home",
        line1="1 Infinite Loop",
        city="Cupertino",
        state="CA",
        postal_code="95014",
        country="US",
        is_default=True,
    )
    payment_method = SavedPaymentMethod(
        customer_id=uuid.UUID(customer_id),
        processor_token="pm_tok_abc",
        brand="visa",
        last4="4242",
        exp_month=12,
        exp_year=2030,
        is_default=True,
    )
    db_session.add_all([address, payment_method])
    await db_session.commit()
    await db_session.refresh(address)
    await db_session.refresh(payment_method)
    return address, payment_method


class TestOneClickToken:
    async def test_issue_token(self, client, auth_headers):
        resp = await client.post("/api/v1/one-click/token", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert "token" in body and len(body["token"]) > 20

    async def test_token_requires_auth(self, client):
        resp = await client.post("/api/v1/one-click/token")
        assert resp.status_code in (401, 403)


class TestOneClickData:
    async def test_list_saved_addresses(self, client, auth_headers, db_session, customer_id):
        await _seed_address_and_payment(db_session, customer_id)
        resp = await client.get("/api/v1/one-click/addresses", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 1
        assert resp.json()[0]["city"] == "Cupertino"

    async def test_list_saved_payment_methods(self, client, auth_headers, db_session, customer_id):
        await _seed_address_and_payment(db_session, customer_id)
        resp = await client.get("/api/v1/one-click/payment-methods", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()[0]["last4"] == "4242"


class TestOneClickCheckout:
    async def test_checkout_success(self, client, auth_headers, db_session, customer_id):
        address, payment_method = await _seed_address_and_payment(db_session, customer_id)
        token_resp = await client.post("/api/v1/one-click/token", headers=auth_headers)
        token = token_resp.json()["token"]

        resp = await client.post(
            "/api/v1/one-click/checkout",
            json={
                "token": token,
                "saved_address_id": str(address.id),
                "saved_payment_method_id": str(payment_method.id),
                "order_id": str(uuid.uuid4()),
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "confirmed"

    async def test_checkout_rejects_reused_token(self, client, auth_headers, db_session, customer_id):
        address, payment_method = await _seed_address_and_payment(db_session, customer_id)
        token_resp = await client.post("/api/v1/one-click/token", headers=auth_headers)
        token = token_resp.json()["token"]

        checkout_body = {
            "token": token,
            "saved_address_id": str(address.id),
            "saved_payment_method_id": str(payment_method.id),
            "order_id": str(uuid.uuid4()),
        }
        first = await client.post("/api/v1/one-click/checkout", json=checkout_body, headers=auth_headers)
        assert first.status_code == 200

        second = await client.post("/api/v1/one-click/checkout", json=checkout_body, headers=auth_headers)
        assert second.status_code == 401

    async def test_checkout_rejects_invalid_token(self, client, auth_headers, db_session, customer_id):
        address, payment_method = await _seed_address_and_payment(db_session, customer_id)
        resp = await client.post(
            "/api/v1/one-click/checkout",
            json={
                "token": "not-a-real-token",
                "saved_address_id": str(address.id),
                "saved_payment_method_id": str(payment_method.id),
                "order_id": str(uuid.uuid4()),
            },
            headers=auth_headers,
        )
        assert resp.status_code == 401
