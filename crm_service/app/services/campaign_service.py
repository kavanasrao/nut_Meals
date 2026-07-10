from uuid import UUID

from app.models.campaign import Campaign
from app.models.enums import CampaignStatus, CampaignType
from app.repositories.campaign_repository import (
    CampaignRepository,
)
from app.schemas.campaign import (
    CampaignCreate,
    CampaignUpdate,
)


class CampaignService:
    def __init__(
        self,
        repository: CampaignRepository,
    ) -> None:
        self.repository = repository

    async def create_campaign(
        self,
        data: CampaignCreate,
    ) -> Campaign:
        campaign = Campaign(**data.model_dump())
        return await self.repository.create(campaign)

    async def get_campaign(
        self,
        campaign_id: UUID,
    ) -> Campaign | None:
        return await self.repository.get_by_id(campaign_id)

    async def get_campaign_by_name(
        self,
        name: str,
    ) -> Campaign | None:
        return await self.repository.get_by_name(name)

    async def list_campaigns(
        self,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Campaign]:
        return await self.repository.get_all(skip, limit)

    async def get_campaigns_by_status(
        self,
        status: CampaignStatus,
    ) -> list[Campaign]:
        return await self.repository.get_by_status(status)

    async def get_campaigns_by_type(
        self,
        campaign_type: CampaignType,
    ) -> list[Campaign]:
        return await self.repository.get_by_type(campaign_type)

    async def get_creator_campaigns(
        self,
        creator_id: UUID,
    ) -> list[Campaign]:
        return await self.repository.get_by_creator(creator_id)

    async def update_campaign(
        self,
        campaign_id: UUID,
        data: CampaignUpdate,
    ) -> Campaign | None:
        campaign = await self.repository.get_by_id(campaign_id)

        if campaign is None:
            return None

        return await self.repository.update(
            campaign,
            data.model_dump(exclude_unset=True),
        )

    async def update_status(
        self,
        campaign_id: UUID,
        status: CampaignStatus,
    ) -> Campaign | None:
        return await self.repository.update_status(
            campaign_id,
            status,
        )

    async def delete_campaign(
        self,
        campaign_id: UUID,
    ) -> bool:
        return await self.repository.soft_delete(campaign_id)