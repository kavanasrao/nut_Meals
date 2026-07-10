from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer_preference import CustomerPreference
from app.repositories.base_repository import BaseRepository


class CustomerPreferenceRepository(BaseRepository[CustomerPreference]):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(CustomerPreference, db)

    async def get_by_customer_id(
        self,
        customer_id: UUID,
    ) -> CustomerPreference | None:
        result = await self.db.execute(
            select(CustomerPreference).where(
                CustomerPreference.customer_id == customer_id,
                CustomerPreference.is_deleted.is_(False),
            )
        )
        return result.scalar_one_or_none()

    async def enable_all_notifications(
        self,
        customer_id: UUID,
    ) -> CustomerPreference | None:
        preference = await self.get_by_customer_id(customer_id)

        if preference is None:
            return None

        preference.email_notifications = True
        preference.sms_notifications = True
        preference.whatsapp_notifications = True
        preference.push_notifications = True

        await self.db.commit()
        await self.db.refresh(preference)

        return preference

    async def disable_all_notifications(
        self,
        customer_id: UUID,
    ) -> CustomerPreference | None:
        preference = await self.get_by_customer_id(customer_id)

        if preference is None:
            return None

        preference.email_notifications = False
        preference.sms_notifications = False
        preference.whatsapp_notifications = False
        preference.push_notifications = False

        await self.db.commit()
        await self.db.refresh(preference)

        return preference