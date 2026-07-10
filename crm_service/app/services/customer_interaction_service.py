from uuid import UUID

from app.models.customer_interaction import CustomerInteraction
from app.models.enums import InteractionType
from app.repositories.customer_interaction_repository import (
    CustomerInteractionRepository,
)
from app.schemas.customer_interaction import (
    CustomerInteractionCreate,
    CustomerInteractionUpdate,
)


class CustomerInteractionService:
    def __init__(
        self,
        repository: CustomerInteractionRepository,
    ) -> None:
        self.repository = repository

    async def create_interaction(
        self,
        data: CustomerInteractionCreate,
    ) -> CustomerInteraction:
        interaction = CustomerInteraction(**data.model_dump())
        return await self.repository.create(interaction)

    async def get_interaction(
        self,
        interaction_id: UUID,
    ) -> CustomerInteraction | None:
        return await self.repository.get_by_id(interaction_id)

    async def get_customer_interactions(
        self,
        customer_id: UUID,
    ) -> list[CustomerInteraction]:
        return await self.repository.get_by_customer_id(customer_id)

    async def get_interactions_by_type(
        self,
        customer_id: UUID,
        interaction_type: InteractionType,
    ) -> list[CustomerInteraction]:
        return await self.repository.get_by_type(
            customer_id,
            interaction_type,
        )

    async def get_staff_interactions(
        self,
        staff_id: UUID,
    ) -> list[CustomerInteraction]:
        return await self.repository.get_by_staff(staff_id)

    async def update_interaction(
        self,
        interaction_id: UUID,
        data: CustomerInteractionUpdate,
    ) -> CustomerInteraction | None:
        interaction = await self.repository.get_by_id(interaction_id)

        if interaction is None:
            return None

        return await self.repository.update(
            interaction,
            data.model_dump(exclude_unset=True),
        )

    async def delete_interaction(
        self,
        interaction_id: UUID,
    ) -> bool:
        return await self.repository.soft_delete(interaction_id)