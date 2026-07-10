from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.models.enums import CampaignStatus, CampaignType
from app.schemas.base import BaseSchema, TimestampSchema


class CampaignBase(BaseSchema):
    name: str = Field(..., max_length=150)

    campaign_type: CampaignType

    status: CampaignStatus = CampaignStatus.DRAFT

    subject: str | None = Field(
        default=None,
        max_length=255,
    )

    content: str

    scheduled_at: datetime | None = None

    started_at: datetime | None = None

    completed_at: datetime | None = None

    created_by: UUID


class CampaignCreate(CampaignBase):
    pass


class CampaignUpdate(BaseSchema):
    name: str | None = Field(default=None, max_length=150)

    campaign_type: CampaignType | None = None

    status: CampaignStatus | None = None

    subject: str | None = Field(
        default=None,
        max_length=255,
    )

    content: str | None = None

    scheduled_at: datetime | None = None

    started_at: datetime | None = None

    completed_at: datetime | None = None


class CampaignResponse(
    CampaignBase,
    TimestampSchema,
):
    pass


class CampaignListResponse(BaseSchema):
    total: int
    items: list[CampaignResponse]
    