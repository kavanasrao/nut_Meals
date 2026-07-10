from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.database import get_db
from app.repositories.campaign_repository import CampaignRepository
from app.schema.campaign import (
    CampaignCreate,
    CampaignResponse,
    CampaignUpdate,
)
from app.services.campaign_service import CampaignService

router = APIRouter(
    prefix="/campaigns",
    tags=["Campaigns"],
)


def get_service(
    db: AsyncSession = Depends(get_db),
) -> CampaignService:
    repository = CampaignRepository(db)
    return CampaignService(repository)


@router.post(
    "/",
    response_model=CampaignResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_campaign(
    payload: CampaignCreate,
    service: CampaignService = Depends(get_service),
):
    return await service.create_campaign(payload)


@router.get(
    "/{campaign_id}",
    response_model=CampaignResponse,
)
async def get_campaign(
    campaign_id: UUID,
    service: CampaignService = Depends(get_service),
):
    campaign = await service.get_campaign(campaign_id)

    if campaign is None:
        raise HTTPException(
            status_code=404,
            detail="Campaign not found",
        )

    return campaign


@router.get("/")
async def list_campaigns(
    skip: int = 0,
    limit: int = 100,
    service: CampaignService = Depends(get_service),
):
    return await service.list_campaigns(skip, limit)


@router.put(
    "/{campaign_id}",
    response_model=CampaignResponse,
)
async def update_campaign(
    campaign_id: UUID,
    payload: CampaignUpdate,
    service: CampaignService = Depends(get_service),
):
    campaign = await service.update_campaign(
        campaign_id,
        payload,
    )

    if campaign is None:
        raise HTTPException(
            status_code=404,
            detail="Campaign not found",
        )

    return campaign


@router.delete("/{campaign_id}")
async def delete_campaign(
    campaign_id: UUID,
    service: CampaignService = Depends(get_service),
):
    deleted = await service.delete_campaign(campaign_id)

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="Campaign not found",
        )

    return {
        "message": "Campaign deleted successfully"
    }
