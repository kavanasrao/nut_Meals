from uuid import UUID

from app.models.customer_tag import CustomerTag
from app.repositories.customer_tag_repository import (
    CustomerTagRepository,
)
from app.schemas.customer_tag import (
    CustomerTagCreate,
    CustomerTagUpdate,
)


class CustomerTagService:
    def __init__(
        self,
        repository: CustomerTagRepository,
    ) -> None:
        self.repository = repository

    async def create_tag(
        self,
        data: CustomerTagCreate,
    ) -> CustomerTag:
        tag = CustomerTag(**data.model_dump())
        return await self.repository.create(tag)

    async def get_tag(
        self,
        tag_id: UUID,
    ) -> CustomerTag | None:
        return await self.repository.get_by_id(tag_id)

    async def get_customer_tags(
        self,
        customer_id: UUID,
    ) -> list[CustomerTag]:
        return await self.repository.get_by_customer_id(customer_id)

    async def get_tag_by_name(
        self,
        customer_id: UUID,
        name: str,
    ) -> CustomerTag | None:
        return await self.repository.get_by_name(
            customer_id,
            name,
        )

    async def update_tag(
        self,
        tag_id: UUID,
        data: CustomerTagUpdate,
    ) -> CustomerTag | None:
        tag = await self.repository.get_by_id(tag_id)

        if tag is None:
            return None

        return await self.repository.update(
            tag,
            data.model_dump(exclude_unset=True),
        )

    async def delete_tag(
        self,
        customer_id: UUID,
        name: str,
    ) -> bool:
        return await self.repository.delete_by_name(
            customer_id,
            name,
        )