"""Saved address routes (scoped to the authenticated user).

GET    /api/v1/addresses               — list my addresses
POST   /api/v1/addresses               — create an address
GET    /api/v1/addresses/{address_id}  — get one address
PATCH  /api/v1/addresses/{address_id}  — update an address
DELETE /api/v1/addresses/{address_id}  — delete an address
PATCH  /api/v1/addresses/{address_id}/default — mark as default
"""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_active_user
from app.core.db import get_db
from app.models.audit_log import AuditAction
from app.models.user import User
from app.schemas.address import (
    AddressCreate,
    AddressListResponse,
    AddressOut,
    AddressUpdate,
)
from app.services.address_service import AddressService
from app.services.audit_service import AuditService

router = APIRouter(prefix="/addresses", tags=["addresses"])


@router.get("", response_model=AddressListResponse, summary="List my saved addresses")
async def list_addresses(
    db: AsyncSession = Depends(get_db), user: User = Depends(require_active_user)
) -> AddressListResponse:
    svc = AddressService(db)
    addresses, total = await svc.list_addresses(user.id)
    return AddressListResponse(
        addresses=[AddressOut.model_validate(a) for a in addresses], total=total
    )


@router.post(
    "",
    response_model=AddressOut,
    status_code=status.HTTP_201_CREATED,
    summary="Add a new address",
)
async def create_address(
    body: AddressCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_active_user),
) -> AddressOut:
    svc = AddressService(db)
    address = await svc.create_address(user.id, body)
    await AuditService(db).record(
        user_id=user.id, action=AuditAction.ADDRESS_CREATE, description=f"Added address '{address.label}'"
    )
    return AddressOut.model_validate(address)


@router.get("/{address_id}", response_model=AddressOut, summary="Get one address")
async def get_address(
    address_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_active_user),
) -> AddressOut:
    svc = AddressService(db)
    address = await svc.get_address(user.id, address_id)
    if address is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Address not found")
    return AddressOut.model_validate(address)


@router.patch("/{address_id}", response_model=AddressOut, summary="Update an address")
async def update_address(
    address_id: UUID,
    body: AddressUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_active_user),
) -> AddressOut:
    svc = AddressService(db)
    address = await svc.update_address(user.id, address_id, body)
    if address is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Address not found")
    await AuditService(db).record(
        user_id=user.id, action=AuditAction.ADDRESS_UPDATE, description=f"Updated address '{address.label}'"
    )
    return AddressOut.model_validate(address)


@router.delete(
    "/{address_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete an address"
)
async def delete_address(
    address_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_active_user),
) -> None:
    svc = AddressService(db)
    deleted = await svc.delete_address(user.id, address_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Address not found")
    await AuditService(db).record(
        user_id=user.id, action=AuditAction.ADDRESS_DELETE, description="Deleted address"
    )


@router.patch(
    "/{address_id}/default", response_model=AddressOut, summary="Mark an address as default"
)
async def set_default_address(
    address_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_active_user),
) -> AddressOut:
    svc = AddressService(db)
    address = await svc.set_default(user.id, address_id)
    if address is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Address not found")
    await AuditService(db).record(
        user_id=user.id,
        action=AuditAction.ADDRESS_SET_DEFAULT,
        description=f"Set default address to '{address.label}'",
    )
    return AddressOut.model_validate(address)
