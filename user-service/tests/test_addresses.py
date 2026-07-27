"""Tests for saved address CRUD endpoints."""
from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from tests.conftest import auth_headers

pytestmark = pytest.mark.asyncio


def _address_payload(**overrides) -> dict:
    payload = {
        "label": "Home",
        "address_type": "home",
        "full_name": "Jane Doe",
        "phone": "+919876543210",
        "line1": "123 MG Road",
        "city": "Bengaluru",
        "state": "Karnataka",
        "country": "India",
        "postal_code": "560001",
    }
    payload.update(overrides)
    return payload


async def test_create_first_address_becomes_default(client: AsyncClient, user: User):
    resp = await client.post(
        "/api/v1/addresses", json=_address_payload(), headers=auth_headers(user)
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["is_default"] is True


async def test_second_address_is_not_default_unless_requested(client: AsyncClient, user: User):
    headers = auth_headers(user)
    await client.post("/api/v1/addresses", json=_address_payload(label="Home"), headers=headers)
    resp = await client.post(
        "/api/v1/addresses", json=_address_payload(label="Work"), headers=headers
    )
    assert resp.status_code == 201
    assert resp.json()["is_default"] is False


async def test_only_one_address_is_default_at_a_time(client: AsyncClient, user: User):
    headers = auth_headers(user)
    first = await client.post(
        "/api/v1/addresses", json=_address_payload(label="Home"), headers=headers
    )
    second = await client.post(
        "/api/v1/addresses",
        json=_address_payload(label="Work", is_default=True),
        headers=headers,
    )
    assert second.json()["is_default"] is True

    listing = await client.get("/api/v1/addresses", headers=headers)
    default_count = sum(1 for a in listing.json()["addresses"] if a["is_default"])
    assert default_count == 1


async def test_set_default_endpoint_switches_default(client: AsyncClient, user: User):
    headers = auth_headers(user)
    first = await client.post(
        "/api/v1/addresses", json=_address_payload(label="Home"), headers=headers
    )
    second = await client.post(
        "/api/v1/addresses", json=_address_payload(label="Work"), headers=headers
    )
    second_id = second.json()["id"]

    resp = await client.patch(f"/api/v1/addresses/{second_id}/default", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["is_default"] is True

    first_id = first.json()["id"]
    refreshed_first = await client.get(f"/api/v1/addresses/{first_id}", headers=headers)
    assert refreshed_first.json()["is_default"] is False


async def test_update_address(client: AsyncClient, user: User):
    headers = auth_headers(user)
    created = await client.post(
        "/api/v1/addresses", json=_address_payload(), headers=headers
    )
    address_id = created.json()["id"]

    resp = await client.patch(
        f"/api/v1/addresses/{address_id}", json={"city": "Mumbai"}, headers=headers
    )
    assert resp.status_code == 200
    assert resp.json()["city"] == "Mumbai"


async def test_delete_address_promotes_another_to_default(client: AsyncClient, user: User):
    headers = auth_headers(user)
    first = await client.post(
        "/api/v1/addresses", json=_address_payload(label="Home"), headers=headers
    )
    await client.post("/api/v1/addresses", json=_address_payload(label="Work"), headers=headers)

    first_id = first.json()["id"]
    resp = await client.delete(f"/api/v1/addresses/{first_id}", headers=headers)
    assert resp.status_code == 204

    listing = await client.get("/api/v1/addresses", headers=headers)
    addresses = listing.json()["addresses"]
    assert len(addresses) == 1
    assert addresses[0]["is_default"] is True


async def test_cannot_access_another_users_address(
    client: AsyncClient, db_session: AsyncSession, user: User
):
    from tests.conftest import create_user

    other_user = await create_user(db_session, email="other@example.com")
    created = await client.post(
        "/api/v1/addresses", json=_address_payload(), headers=auth_headers(user)
    )
    address_id = created.json()["id"]

    resp = await client.get(f"/api/v1/addresses/{address_id}", headers=auth_headers(other_user))
    assert resp.status_code == 404


async def test_addresses_require_authentication(client: AsyncClient):
    resp = await client.get("/api/v1/addresses")
    assert resp.status_code == 401
