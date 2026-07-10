from uuid import UUID

from app.models.customer_profile import CustomerProfile
from app.repositories.customer_profile_repository import (
    CustomerProfileRepository,
)
from app.schemas.customer_profile import (
    CustomerProfileCreate,
    CustomerProfileUpdate,
)


class CustomerProfileService:
    def __init__(
        self,
        repository: CustomerProfileRepository,
    ) -> None:
        self.repository = repository

    async def create_customer(
        self,
        data: CustomerProfileCreate,
    ) -> CustomerProfile:
        customer = CustomerProfile(**data.model_dump())
        return await self.repository.create(customer)

    async def get_customer(
        self,
        customer_id: UUID,
    ) -> CustomerProfile | None:
        return await self.repository.get_by_id(customer_id)

    async def get_customer_by_user(
        self,
        user_id: UUID,
    ) -> CustomerProfile | None:
        return await self.repository.get_by_user_id(user_id)

    async def get_customer_by_code(
        self,
        customer_code: str,
    ) -> CustomerProfile | None:
        return await self.repository.get_by_customer_code(customer_code)

    async def list_customers(
        self,
        skip: int = 0,
        limit: int = 100,
    ):
        return await self.repository.get_all(skip, limit)

    async def update_customer(
        self,
        customer_id: UUID,
        data: CustomerProfileUpdate,
    ) -> CustomerProfile | None:
        customer = await self.repository.get_by_id(customer_id)

        if customer is None:
            return None

        return await self.repository.update(
            customer,
            data.model_dump(exclude_unset=True),
        )

    async def delete_customer(
        self,
        customer_id: UUID,
    ) -> bool:
        return await self.repository.soft_delete(customer_id)

    async def update_loyalty_points(
        self,
        customer_id: UUID,
        points: int,
    ):
        return await self.repository.update_loyalty_points(
            customer_id,
            points,
        )

    async def update_lifetime_value(
        self,
        customer_id: UUID,
        value: float,
    ):
        return await self.repository.update_lifetime_value(
            customer_id,
            value,
        )