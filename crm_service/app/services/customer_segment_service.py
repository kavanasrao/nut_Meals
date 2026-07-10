from uuid import UUID

from app.models.customer_segment import CustomerSegment
from app.repositories.customer_segment_repository import (
    CustomerSegmentRepository,
)
from app.schemas.customer_segment import (
    CustomerSegmentCreate,
    CustomerSegmentUpdate,
)


class CustomerSegmentService:
    def __init__(
        self,
        repository: CustomerSegmentRepository,
    ) -> None:
        self.repository = repository

    async def create_segment(
        self,
        data: CustomerSegmentCreate,
    ) -> CustomerSegment:
        segment = CustomerSegment(**data.model_dump())
        return await self.repository.create(segment)

    async def get_segment(
        self,
        segment_id: UUID,
    ) -> CustomerSegment | None:
        return await self.repository.get_by_id(segment_id)

    async def get_customer_segments(
        self,
        customer_id: UUID,
    ) -> list[CustomerSegment]:
        return await self.repository.get_by_customer_id(customer_id)

    async def get_dynamic_segments(
        self,
    ) -> list[CustomerSegment]:
        return await self.repository.get_dynamic_segments()

    async def get_segment_by_name(
        self,
        customer_id: UUID,
        name: str,
    ) -> CustomerSegment | None:
        return await self.repository.get_by_name(
            customer_id,
            name,
        )

    async def update_segment(
        self,
        segment_id: UUID,
        data: CustomerSegmentUpdate,
    ) -> CustomerSegment | None:
        segment = await self.repository.get_by_id(segment_id)

        if segment is None:
            return None

        return await self.repository.update(
            segment,
            data.model_dump(exclude_unset=True),
        )

    async def delete_segment(
        self,
        segment_id: UUID,
    ) -> bool:
        return await self.repository.soft_delete(segment_id)