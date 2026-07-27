"""Tests for internal (service-to-service) address endpoints.

These simulate how the Order Service / Logistics Service would call this
service directly (via the shared internal token), not via user JWTs.
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.core.config import settings
from app.models.user import User
from tests.conftest import auth_headers

pytestmark = pytest.mark.asyncio

INTERNAL_HEADERS = {"X-Internal-Service-Token": settings.INTERNAL_SERVICE_TOKEN}


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


async def test_internal_get_address_by_id(client: AsyncClient, user: User):
    created = await client.post(
        "/api/v1/addresses", json=_address_payload(), headers=auth_headers(user)
    )
    address_id = created.json()["id"]

    resp = await client.get(f"/api/v1/internal/addresses/{address_id}", headers=INTERNAL_HEADERS)
    assert resp.status_code == 200
    body = resp.json()
    assert body["address_id"] == address_id
    assert body["city"] == "Bengaluru"
    # Snapshot must not leak ownership/internal bookkeeping fields.
    assert "user_id" not in body
    assert "is_default" not in body


async def test_internal_get_default_address(client: AsyncClient, user: User):
    await client.post("/api/v1/addresses", json=_address_payload(), headers=auth_headers(user))

    resp = await client.get(
        f"/api/v1/internal/users/{user.id}/default-address", headers=INTERNAL_HEADERS
    )
    assert resp.status_code == 200
    assert resp.json()["city"] == "Bengaluru"


async def test_internal_default_address_404_when_none_saved(client: AsyncClient, user: User):
    resp = await client.get(
        f"/api/v1/internal/users/{user.id}/default-address", headers=INTERNAL_HEADERS
    )
    assert resp.status_code == 404


async def test_internal_list_user_addresses(client: AsyncClient, user: User):
    headers = auth_headers(user)
    await client.post("/api/v1/addresses", json=_address_payload(label="Home"), headers=headers)
    await client.post("/api/v1/addresses", json=_address_payload(label="Work"), headers=headers)

    resp = await client.get(
        f"/api/v1/internal/users/{user.id}/addresses", headers=INTERNAL_HEADERS
    )
    assert resp.status_code == 200
    assert len(resp.json()) == 2


async def test_internal_endpoints_reject_missing_token(client: AsyncClient, user: User):
    resp = await client.get(f"/api/v1/internal/users/{user.id}/addresses")
    assert resp.status_code == 401


async def test_internal_endpoints_reject_wrong_token(client: AsyncClient, user: User):
    resp = await client.get(
        f"/api/v1/internal/users/{user.id}/addresses",
        headers={"X-Internal-Service-Token": "totally-wrong-token"},
    )
    assert resp.status_code == 401


async def test_internal_endpoints_not_usable_with_a_user_jwt(client: AsyncClient, user: User):
    """A user's own bearer token must not substitute for the internal
    service token — these are two separate trust boundaries."""
    resp = await client.get(
        f"/api/v1/internal/users/{user.id}/addresses", headers=auth_headers(user)
    )
    assert resp.status_code == 401


async def test_internal_address_lookup_404_for_unknown_id(client: AsyncClient):
    resp = await client.get(
        "/api/v1/internal/addresses/00000000-0000-0000-0000-000000000000",
        headers=INTERNAL_HEADERS,
    )
    assert resp.status_code == 404
