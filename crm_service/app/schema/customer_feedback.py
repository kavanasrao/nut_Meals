from uuid import UUID

from pydantic import Field

from app.models.enums import FeedbackRating
from app.schemas.base import BaseSchema, TimestampSchema


class CustomerFeedbackBase(BaseSchema):
    customer_id: UUID

    order_id: UUID | None = None

    ticket_id: UUID | None = None

    rating: FeedbackRating

    category: str = Field(..., max_length=100)

    title: str | None = Field(
        default=None,
        max_length=255,
    )

    comments: str | None = None

    is_resolved: bool = False


class CustomerFeedbackCreate(CustomerFeedbackBase):
    pass


class CustomerFeedbackUpdate(BaseSchema):
    rating: FeedbackRating | None = None

    category: str | None = Field(
        default=None,
        max_length=100,
    )

    title: str | None = Field(
        default=None,
        max_length=255,
    )

    comments: str | None = None

    is_resolved: bool | None = None


class CustomerFeedbackResponse(
    CustomerFeedbackBase,
    TimestampSchema,
):
    pass


class CustomerFeedbackListResponse(BaseSchema):
    total: int
    items: list[CustomerFeedbackResponse]
    