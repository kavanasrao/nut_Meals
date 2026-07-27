"""Saved addresses API endpoints."""
from typing import Annotated, List
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import TokenPayload, require_customer
from app.db.session import get_db
from app.schemas.address import AddressCreate, AddressResponse, AddressUpdate
from app.services.address_service import AddressService

router = APIRouter(prefix="/addresses", tags=["Addresses"])
CurrentUser = Annotated[TokenPayload, Depends(require_customer)]


@router.get("", response_model=List[AddressResponse], summary="List saved addresses")
async def list_addresses(user: CurrentUser, db: AsyncSession = Depends(get_db)):
    return await AddressService(db).list_addresses(user.user_id)


@router.post("", response_model=AddressResponse, status_code=201, summary="Create address")
async def create_address(
    payload: AddressCreate, user: CurrentUser, db: AsyncSession = Depends(get_db)
):
    return await AddressService(db).create_address(user.user_id, payload)


@router.put("/{address_id}", response_model=AddressResponse, summary="Update address")
async def update_address(
    address_id: UUID,
    payload: AddressUpdate,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    return await AddressService(db).update_address(user.user_id, address_id, payload)


@router.delete("/{address_id}", status_code=204, summary="Delete address")
async def delete_address(
    address_id: UUID, user: CurrentUser, db: AsyncSession = Depends(get_db)
):
    await AddressService(db).delete_address(user.user_id, address_id)


@router.patch("/{address_id}/default", response_model=AddressResponse,
              summary="Set address as default")
async def set_default(
    address_id: UUID, user: CurrentUser, db: AsyncSession = Depends(get_db)
):
    return await AddressService(db).set_default(user.user_id, address_id)
