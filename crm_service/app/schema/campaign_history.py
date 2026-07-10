from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.schemas.base import BaseSchema, TimestampSchema


class CampaignHistoryBase(BaseSchema):
    campaign_id: UUID

    customer_id: UUID | None = None

    event: str = Field(..., max_length=50)

    channel: str = Field(..., max_length=30)

    status: str = Field(..., max_length=30)

    message_id: str | None = Field(
        default=None,
        max_length=150,
    )

    response_code: int | None = None

    response_message: str | None = Field(
        default=None,
        max_length=255,
    )

    event_time: datetime

    is_success: bool = True


class CampaignHistoryCreate(CampaignHistoryBase):
    pass


class CampaignHistoryUpdate(BaseSchema):
    event: str | None = Field(default=None, max_length=50)
    channel: str | None = Field(default=None, max_length=30)
    status: str | None = Field(default=None, max_length=30)
    message_id: str | None = Field(default=None, max_length=150)
    response_code: int | None = None
    response_message: str | None = Field(default=None, max_length=255)
    event_time: datetime | None = None
    is_success: bool | None = None


class CampaignHistoryResponse(
    CampaignHistoryBase,
    TimestampSchema,
):
    pass


class CampaignHistoryListResponse(BaseSchema):
    total: int
    items: list[CampaignHistoryResponse]
    