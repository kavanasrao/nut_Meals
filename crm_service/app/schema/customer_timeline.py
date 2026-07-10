from uuid import UUID

from pydantic import Field

from app.models.enums import TimelineEvent
from app.schemas.base import BaseSchema, TimestampSchema


class CustomerTimelineBase(BaseSchema):
    customer_id: UUID

    event_type: TimelineEvent

    title: str = Field(..., max_length=150)

    description: str | None = None

    reference_type: str | None = Field(default=None, max_length=50)

    reference_id: UUID | None = None

    metadata: dict | None = None


class CustomerTimelineCreate(CustomerTimelineBase):
    pass


class CustomerTimelineUpdate(BaseSchema):
    event_type: TimelineEvent | None = None
    title: str | None = Field(default=None, max_length=150)
    description: str | None = None
    reference_type: str | None = Field(default=None, max_length=50)
    reference_id: UUID | None = None
    metadata: dict | None = None


class CustomerTimelineResponse(
    CustomerTimelineBase,
    TimestampSchema,
):
    pass


class CustomerTimelineListResponse(BaseSchema):
    total: int
    items: list[CustomerTimelineResponse]
    