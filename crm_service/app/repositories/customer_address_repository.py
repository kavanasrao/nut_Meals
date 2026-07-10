from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer_address import CustomerAddress
from app.repositories.base_repository import BaseRepository


class CustomerAddressRepository(BaseRepository[CustomerAddress]):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(CustomerAddress, db)

    async def get_by_customer_id(
        self,
        customer_id: UUID,
    ) -> list[CustomerAddress]:
        result = await self.db.execute(
            select(CustomerAddress)
            .where(
                CustomerAddress.customer_id == customer_id,
                CustomerAddress.is_deleted.is_(False),
            )
            .order_by(CustomerAddress.created_at.desc())
        )
        return result.scalars().all()

    async def get_default_address(
        self,
        customer_id: UUID,
    ) -> CustomerAddress | None:
        result = await self.db.execute(
            select(CustomerAddress).where(
                CustomerAddress.customer_id == customer_id,
                CustomerAddress.is_default.is_(True),
                CustomerAddress.is_deleted.is_(False),
            )
        )
        return result.scalar_one_or_none()

    async def set_default_address(
        self,
        customer_id: UUID,
        address_id: UUID,
    ) -> CustomerAddress | None:
        addresses = await self.get_by_customer_id(customer_id)

        for address in addresses:
            address.is_default = address.id == address_id

        await self.db.commit()

        return await self.get_by_id(address_id)