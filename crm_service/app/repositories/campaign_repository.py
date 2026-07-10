from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.campaign import Campaign
from app.models.enums import CampaignStatus, CampaignType
from app.repositories.base_repository import BaseRepository


class CampaignRepository(BaseRepository[Campaign]):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(Campaign, db)

    async def get_by_name(
        self,
        name: str,
    ) -> Campaign | None:
        result = await self.db.execute(
            select(Campaign).where(
                Campaign.name == name,
                Campaign.is_deleted.is_(False),
            )
        )
        return result.scalar_one_or_none()

    async def get_by_status(
        self,
        status: CampaignStatus,
    ) -> list[Campaign]:
        result = await self.db.execute(
            select(Campaign)
            .where(
                Campaign.status == status,
                Campaign.is_deleted.is_(False),
            )
            .order_by(desc(Campaign.created_at))
        )
        return result.scalars().all()

    async def get_by_type(
        self,
        campaign_type: CampaignType,
    ) -> list[Campaign]:
        result = await self.db.execute(
            select(Campaign)
            .where(
                Campaign.campaign_type == campaign_type,
                Campaign.is_deleted.is_(False),
            )
            .order_by(desc(Campaign.created_at))
        )
        return result.scalars().all()

    async def get_by_creator(
        self,
        creator_id: UUID,
    ) -> list[Campaign]:
        result = await self.db.execute(
            select(Campaign)
            .where(
                Campaign.created_by == creator_id,
                Campaign.is_deleted.is_(False),
            )
            .order_by(desc(Campaign.created_at))
        )
        return result.scalars().all()

    async def update_status(
        self,
        campaign_id: UUID,
        status: CampaignStatus,
    ) -> Campaign | None:
        campaign = await self.get_by_id(campaign_id)

        if campaign is None:
            return None

        campaign.status = status

        await self.db.commit()
        await self.db.refresh(campaign)

        return campaign