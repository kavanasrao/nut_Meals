from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer_tag import CustomerTag
from app.repositories.base_repository import BaseRepository


class CustomerTagRepository(BaseRepository[CustomerTag]):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(CustomerTag, db)

    async def get_by_customer_id(
        self,
        customer_id: UUID,
    ) -> list[CustomerTag]:
        result = await self.db.execute(
            select(CustomerTag)
            .where(
                CustomerTag.customer_id == customer_id,
                CustomerTag.is_deleted.is_(False),
            )
            .order_by(CustomerTag.name)
        )
        return result.scalars().all()

    async def get_by_name(
        self,
        customer_id: UUID,
        name: str,
    ) -> CustomerTag | None:
        result = await self.db.execute(
            select(CustomerTag).where(
                CustomerTag.customer_id == customer_id,
                CustomerTag.name == name,
                CustomerTag.is_deleted.is_(False),
            )
        )
        return result.scalar_one_or_none()

    async def delete_by_name(
        self,
        customer_id: UUID,
        name: str,
    ) -> bool:
        tag = await self.get_by_name(customer_id, name)

        if tag is None:
            return False

        tag.is_deleted = True
        tag.is_active = False

        await self.db.commit()

        return True