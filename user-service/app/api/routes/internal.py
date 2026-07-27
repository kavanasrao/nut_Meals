"""Internal (service-to-service) routes.

These endpoints are consumed by *other* nut_meals microservices, never
directly by end-user clients — they're gated by `verify_internal_service`
(a shared `X-Internal-Service-Token` header) instead of user JWT auth, and
are excluded from the public OpenAPI docs.

Primary use case: linking saved addresses to orders and shipments. The
Order Service calls `/internal/addresses/{address_id}` (or
`/internal/users/{user_id}/default-address`) at checkout time and copies
the returned snapshot onto its own `orders.shipping_address` /
`shipments.delivery_address` columns — it does not hold a live foreign key
into this service's `addresses` table, since a user can edit or delete a
saved address after an order has shipped without that retroactively
changing historical orders.
"""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import verify_internal_service
from app.core.db import get_db
from app.schemas.address import AddressSnapshot
from app.services.address_service import AddressService

router = APIRouter(
    prefix="/internal",
    tags=["internal"],
    dependencies=[Depends(verify_internal_service)],
    include_in_schema=False,
)


def _to_snapshot(address) -> AddressSnapshot:
    return AddressSnapshot(
        address_id=address.id,
        full_name=address.full_name,
        phone=address.phone,
        line1=address.line1,
        line2=address.line2,
        city=address.city,
        state=address.state,
        country=address.country,
        postal_code=address.postal_code,
        landmark=address.landmark,
        latitude=address.latitude,
        longitude=address.longitude,
    )


@router.get(
    "/addresses/{address_id}",
    response_model=AddressSnapshot,
    summary="[internal] Fetch an address snapshot by ID (Order/Logistics services)",
)
async def get_address_snapshot(
    address_id: UUID, db: AsyncSession = Depends(get_db)
) -> AddressSnapshot:
    address = await AddressService(db).get_address_any_user(address_id)
    if address is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Address not found")
    return _to_snapshot(address)


@router.get(
    "/users/{user_id}/default-address",
    response_model=AddressSnapshot,
    summary="[internal] Fetch a user's default address (Order Service, at checkout)",
)
async def get_default_address_snapshot(
    user_id: UUID, db: AsyncSession = Depends(get_db)
) -> AddressSnapshot:
    address = await AddressService(db).get_default_address(user_id)
    if address is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User has no default address"
        )
    return _to_snapshot(address)


@router.get(
    "/users/{user_id}/addresses",
    response_model=list[AddressSnapshot],
    summary="[internal] List all of a user's addresses (Logistics Service, multi-address shipments)",
)
async def list_user_address_snapshots(
    user_id: UUID, db: AsyncSession = Depends(get_db)
) -> list[AddressSnapshot]:
    addresses, _ = await AddressService(db).list_addresses(user_id)
    return [_to_snapshot(a) for a in addresses]
