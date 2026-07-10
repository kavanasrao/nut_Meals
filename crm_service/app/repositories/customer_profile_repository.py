from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer_profile import CustomerProfile
from app.repositories.base_repository import BaseRepository


class CustomerProfileRepository(BaseRepository[CustomerProfile]):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(CustomerProfile, db)

    async def get_by_user_id(
        self,
        user_id: UUID,
    ) -> CustomerProfile | None:
        result = await self.db.execute(
            select(CustomerProfile).where(
                CustomerProfile.user_id == user_id,
                CustomerProfile.is_deleted.is_(False),
            )
        )
        return result.scalar_one_or_none()

    async def get_by_customer_code(
        self,
        customer_code: str,
    ) -> CustomerProfile | None:
        result = await self.db.execute(
            select(CustomerProfile).where(
                CustomerProfile.customer_code == customer_code,
                CustomerProfile.is_deleted.is_(False),
            )
        )
        return result.scalar_one_or_none()

    async def update_loyalty_points(
        self,
        customer_id: UUID,
        points: int,
    ) -> CustomerProfile | None:
        customer = await self.get_by_id(customer_id)

        if customer is None:
            return None

        customer.loyalty_points = points

        await self.db.commit()
        await self.db.refresh(customer)

        return customer

    async def update_lifetime_value(
        self,
        customer_id: UUID,
        value: float,
    ) -> CustomerProfile | None:
        customer = await self.get_by_id(customer_id)

        if customer is None:
            return None

        customer.lifetime_value = value

        await self.db.commit()
        await self.db.refresh(customer)

        return customer