from uuid import UUID

from app.schemas.base import BaseSchema, TimestampSchema


class CampaignAudienceBase(BaseSchema):
    campaign_id: UUID
    customer_id: UUID

    is_sent: bool = False
    is_delivered: bool = False
    is_opened: bool = False
    is_clicked: bool = False


class CampaignAudienceCreate(CampaignAudienceBase):
    pass


class CampaignAudienceUpdate(BaseSchema):
    is_sent: bool | None = None
    is_delivered: bool | None = None
    is_opened: bool | None = None
    is_clicked: bool | None = None


class CampaignAudienceResponse(
    CampaignAudienceBase,
    TimestampSchema,
):
    pass


class CampaignAudienceListResponse(BaseSchema):
    total: int
    items: list[CampaignAudienceResponse]
    