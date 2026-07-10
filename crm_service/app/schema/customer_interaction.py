from uuid import UUID

from pydantic import Field

from app.models.enums import InteractionType
from app.schemas.base import BaseSchema, TimestampSchema


class CustomerInteractionBase(BaseSchema):
    customer_id: UUID

    interaction_type: InteractionType

    subject: str = Field(..., max_length=200)

    message: str

    performed_by: UUID | None = None

    channel_reference: str | None = Field(
        default=None,
        max_length=150,
    )


class CustomerInteractionCreate(CustomerInteractionBase):
    pass


class CustomerInteractionUpdate(BaseSchema):
    interaction_type: InteractionType | None = None

    subject: str | None = Field(
        default=None,
        max_length=200,
    )

    message: str | None = None

    performed_by: UUID | None = None

    channel_reference: str | None = Field(
        default=None,
        max_length=150,
    )


class CustomerInteractionResponse(
    CustomerInteractionBase,
    TimestampSchema,
):
    pass


class CustomerInteractionListResponse(BaseSchema):
    total: int
    items: list[CustomerInteractionResponse]