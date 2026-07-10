from uuid import UUID

from app.models.customer_preference import CustomerPreference
from app.repositories.customer_preference_repository import (
    CustomerPreferenceRepository,
)
from app.schemas.customer_preference import (
    CustomerPreferenceCreate,
    CustomerPreferenceUpdate,
)


class CustomerPreferenceService:
    def __init__(
        self,
        repository: CustomerPreferenceRepository,
    ) -> None:
        self.repository = repository

    async def create_preference(
        self,
        data: CustomerPreferenceCreate,
    ) -> CustomerPreference:
        preference = CustomerPreference(**data.model_dump())
        return await self.repository.create(preference)

    async def get_preference(
        self,
        preference_id: UUID,
    ) -> CustomerPreference | None:
        return await self.repository.get_by_id(preference_id)

    async def get_customer_preference(
        self,
        customer_id: UUID,
    ) -> CustomerPreference | None:
        return await self.repository.get_by_customer_id(customer_id)

    async def update_preference(
        self,
        preference_id: UUID,
        data: CustomerPreferenceUpdate,
    ) -> CustomerPreference | None:
        preference = await self.repository.get_by_id(preference_id)

        if preference is None:
            return None

        return await self.repository.update(
            preference,
            data.model_dump(exclude_unset=True),
        )

    async def enable_notifications(
        self,
        customer_id: UUID,
    ) -> CustomerPreference | None:
        return await self.repository.enable_all_notifications(customer_id)

    async def disable_notifications(
        self,
        customer_id: UUID,
    ) -> CustomerPreference | None:
        return await self.repository.disable_all_notifications(customer_id)

    async def delete_preference(
        self,
        preference_id: UUID,
    ) -> bool:
        return await self.repository.soft_delete(preference_id)