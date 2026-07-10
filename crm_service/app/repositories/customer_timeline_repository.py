from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer_timeline import CustomerTimeline
from app.models.enums import TimelineEvent
from app.repositories.base_repository import BaseRepository


class CustomerTimelineRepository(BaseRepository[CustomerTimeline]):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(CustomerTimeline, db)

    async def get_by_customer_id(
        self,
        customer_id: UUID,
    ) -> list[CustomerTimeline]:
        result = await self.db.execute(
            select(CustomerTimeline)
            .where(
                CustomerTimeline.customer_id == customer_id,
                CustomerTimeline.is_deleted.is_(False),
            )
            .order_by(desc(CustomerTimeline.created_at))
        )
        return result.scalars().all()

    async def get_by_event(
        self,
        customer_id: UUID,
        event_type: TimelineEvent,
    ) -> list[CustomerTimeline]:
        result = await self.db.execute(
            select(CustomerTimeline)
            .where(
                CustomerTimeline.customer_id == customer_id,
                CustomerTimeline.event_type == event_type,
                CustomerTimeline.is_deleted.is_(False),
            )
            .order_by(desc(CustomerTimeline.created_at))
        )
        return result.scalars().all()

    async def get_recent(
        self,
        customer_id: UUID,
        limit: int = 20,
    ) -> list[CustomerTimeline]:
        result = await self.db.execute(
            select(CustomerTimeline)
            .where(
                CustomerTimeline.customer_id == customer_id,
                CustomerTimeline.is_deleted.is_(False),
            )
            .order_by(desc(CustomerTimeline.created_at))
            .limit(limit)
        )
        return result.scalars().all()