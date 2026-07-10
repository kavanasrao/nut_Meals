from uuid import UUID

from app.models.customer_timeline import CustomerTimeline
from app.models.enums import TimelineEvent
from app.repositories.customer_timeline_repository import (
    CustomerTimelineRepository,
)
from app.schemas.customer_timeline import (
    CustomerTimelineCreate,
    CustomerTimelineUpdate,
)


class CustomerTimelineService:
    def __init__(
        self,
        repository: CustomerTimelineRepository,
    ) -> None:
        self.repository = repository

    async def create_event(
        self,
        data: CustomerTimelineCreate,
    ) -> CustomerTimeline:
        timeline = CustomerTimeline(**data.model_dump())
        return await self.repository.create(timeline)

    async def get_event(
        self,
        timeline_id: UUID,
    ) -> CustomerTimeline | None:
        return await self.repository.get_by_id(timeline_id)

    async def get_customer_timeline(
        self,
        customer_id: UUID,
    ) -> list[CustomerTimeline]:
        return await self.repository.get_by_customer_id(customer_id)

    async def get_recent_events(
        self,
        customer_id: UUID,
        limit: int = 20,
    ) -> list[CustomerTimeline]:
        return await self.repository.get_recent(
            customer_id,
            limit,
        )

    async def get_events_by_type(
        self,
        customer_id: UUID,
        event_type: TimelineEvent,
    ) -> list[CustomerTimeline]:
        return await self.repository.get_by_event(
            customer_id,
            event_type,
        )

    async def update_event(
        self,
        timeline_id: UUID,
        data: CustomerTimelineUpdate,
    ) -> CustomerTimeline | None:
        timeline = await self.repository.get_by_id(timeline_id)

        if timeline is None:
            return None

        return await self.repository.update(
            timeline,
            data.model_dump(exclude_unset=True),
        )

    async def delete_event(
        self,
        timeline_id: UUID,
    ) -> bool:
        return await self.repository.soft_delete(timeline_id)