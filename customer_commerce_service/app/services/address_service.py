"""Saved address business logic."""
from typing import List
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.models.address import SavedAddress
from app.schemas.address import AddressCreate, AddressUpdate, AddressResponse


class AddressService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_addresses(self, user_id: UUID) -> List[AddressResponse]:
        result = await self.db.execute(
            select(SavedAddress)
            .where(SavedAddress.user_id == user_id)
            .order_by(SavedAddress.is_default.desc(), SavedAddress.created_at.asc())
        )
        return [AddressResponse.model_validate(a) for a in result.scalars().all()]

    async def create_address(self, user_id: UUID, payload: AddressCreate) -> AddressResponse:
        if payload.is_default:
            await self._unset_defaults(user_id)

        address = SavedAddress(user_id=user_id, **payload.model_dump())
        self.db.add(address)
        await self.db.flush()
        return AddressResponse.model_validate(address)

    async def update_address(
        self, user_id: UUID, address_id: UUID, payload: AddressUpdate
    ) -> AddressResponse:
        address = await self._get_owned(user_id, address_id)
        if payload.is_default:
            await self._unset_defaults(user_id)

        for field, value in payload.model_dump().items():
            setattr(address, field, value)
        await self.db.flush()
        return AddressResponse.model_validate(address)

    async def delete_address(self, user_id: UUID, address_id: UUID) -> None:
        address = await self._get_owned(user_id, address_id)
        await self.db.delete(address)

    async def set_default(self, user_id: UUID, address_id: UUID) -> AddressResponse:
        await self._unset_defaults(user_id)
        address = await self._get_owned(user_id, address_id)
        address.is_default = True
        await self.db.flush()
        return AddressResponse.model_validate(address)

    async def _get_owned(self, user_id: UUID, address_id: UUID) -> SavedAddress:
        result = await self.db.execute(
            select(SavedAddress).where(
                SavedAddress.id == address_id, SavedAddress.user_id == user_id
            )
        )
        address = result.scalar_one_or_none()
        if not address:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Address not found")
        return address

    async def _unset_defaults(self, user_id: UUID) -> None:
        await self.db.execute(
            update(SavedAddress)
            .where(SavedAddress.user_id == user_id, SavedAddress.is_default == True)
            .values(is_default=False)
        )
