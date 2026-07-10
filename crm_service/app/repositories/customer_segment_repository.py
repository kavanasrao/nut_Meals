from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer_segment import CustomerSegment
from app.repositories.base_repository import BaseRepository


class CustomerSegmentRepository(BaseRepository[CustomerSegment]):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(CustomerSegment, db)

    async def get_by_customer_id(
        self,
        customer_id: UUID,
    ) -> list[CustomerSegment]:
        result = await self.db.execute(
            select(CustomerSegment)
            .where(
                CustomerSegment.customer_id == customer_id,
                CustomerSegment.is_deleted.is_(False),
            )
            .order_by(CustomerSegment.name)
        )
        return result.scalars().all()

    async def get_dynamic_segments(self) -> list[CustomerSegment]:
        result = await self.db.execute(
            select(CustomerSegment).where(
                CustomerSegment.is_dynamic.is_(True),
                CustomerSegment.is_deleted.is_(False),
            )
        )
        return result.scalars().all()

    async def get_by_name(
        self,
        customer_id: UUID,
        name: str,
    ) -> CustomerSegment | None:
        result = await self.db.execute(
            select(CustomerSegment).where(
                CustomerSegment.customer_id == customer_id,
                CustomerSegment.name == name,
                CustomerSegment.is_deleted.is_(False),
            )
        )
        return result.scalar_one_or_none()