from uuid import UUID

from pydantic import Field

from app.schemas.base import BaseSchema, TimestampSchema


class CustomerSegmentBase(BaseSchema):
    customer_id: UUID

    name: str = Field(..., max_length=100)
    description: str | None = Field(default=None, max_length=255)

    is_dynamic: bool = True
    rule_expression: str | None = Field(default=None, max_length=500)


class CustomerSegmentCreate(CustomerSegmentBase):
    pass


class CustomerSegmentUpdate(BaseSchema):
    name: str | None = Field(default=None, max_length=100)
    description: str | None = Field(default=None, max_length=255)
    is_dynamic: bool | None = None
    rule_expression: str | None = Field(default=None, max_length=500)


class CustomerSegmentResponse(
    CustomerSegmentBase,
    TimestampSchema,
):
    pass


class CustomerSegmentListResponse(BaseSchema):
    total: int
    items: list[CustomerSegmentResponse]