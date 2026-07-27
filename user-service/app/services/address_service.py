"""Address Service — CRUD saved addresses linked to a user, with a single
"default" address invariant enforced at the application layer."""
from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.address import Address
from app.schemas.address import AddressCreate, AddressUpdate


class AddressService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_addresses(self, user_id: uuid.UUID) -> tuple[list[Address], int]:
        count_r = await self.db.execute(
            select(func.count()).select_from(Address).where(Address.user_id == user_id)
        )
        total = count_r.scalar_one()
        result = await self.db.execute(
            select(Address)
            .where(Address.user_id == user_id)
            .order_by(Address.is_default.desc(), Address.created_at.desc())
        )
        return list(result.scalars().all()), total

    async def get_address(self, user_id: uuid.UUID, address_id: uuid.UUID) -> Optional[Address]:
        result = await self.db.execute(
            select(Address).where(Address.id == address_id, Address.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def create_address(self, user_id: uuid.UUID, data: AddressCreate) -> Address:
        if data.is_default:
            await self._clear_default(user_id)
        else:
            # First address for a user is automatically the default.
            existing_r = await self.db.execute(
                select(func.count()).select_from(Address).where(Address.user_id == user_id)
            )
            if existing_r.scalar_one() == 0:
                data = data.model_copy(update={"is_default": True})

        address = Address(id=uuid.uuid4(), user_id=user_id, **data.model_dump())
        self.db.add(address)
        await self.db.commit()
        await self.db.refresh(address)
        return address

    async def update_address(
        self, user_id: uuid.UUID, address_id: uuid.UUID, data: AddressUpdate
    ) -> Optional[Address]:
        address = await self.get_address(user_id, address_id)
        if address is None:
            return None

        updates = data.model_dump(exclude_unset=True)
        if updates.get("is_default") is True:
            await self._clear_default(user_id)

        for field, value in updates.items():
            setattr(address, field, value)

        await self.db.commit()
        await self.db.refresh(address)
        return address

    async def delete_address(self, user_id: uuid.UUID, address_id: uuid.UUID) -> bool:
        address = await self.get_address(user_id, address_id)
        if address is None:
            return False
        was_default = address.is_default
        await self.db.delete(address)
        await self.db.commit()

        if was_default:
            # Promote the most-recently-created remaining address to default.
            result = await self.db.execute(
                select(Address)
                .where(Address.user_id == user_id)
                .order_by(Address.created_at.desc())
            )
            next_address = result.scalars().first()
            if next_address is not None:
                next_address.is_default = True
                await self.db.commit()
        return True

    async def set_default(self, user_id: uuid.UUID, address_id: uuid.UUID) -> Optional[Address]:
        address = await self.get_address(user_id, address_id)
        if address is None:
            return None
        await self._clear_default(user_id)
        address.is_default = True
        await self.db.commit()
        await self.db.refresh(address)
        return address

    async def _clear_default(self, user_id: uuid.UUID) -> None:
        result = await self.db.execute(
            select(Address).where(Address.user_id == user_id, Address.is_default.is_(True))
        )
        for addr in result.scalars().all():
            addr.is_default = False

    # ── Internal / service-to-service lookups (Order & Logistics services) ──

    async def get_address_any_user(self, address_id: uuid.UUID) -> Optional[Address]:
        """Fetch an address by ID without scoping to a particular owner.
        Used only from internal, service-token-gated endpoints — never
        exposed to end users, since it doesn't check ownership."""
        result = await self.db.execute(select(Address).where(Address.id == address_id))
        return result.scalar_one_or_none()

    async def get_default_address(self, user_id: uuid.UUID) -> Optional[Address]:
        result = await self.db.execute(
            select(Address).where(Address.user_id == user_id, Address.is_default.is_(True))
        )
        return result.scalar_one_or_none()
