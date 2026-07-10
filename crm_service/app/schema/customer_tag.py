from uuid import UUID

from pydantic import Field

from app.schemas.base import BaseSchema, TimestampSchema


class CustomerTagBase(BaseSchema):
    customer_id: UUID

    name: str = Field(..., max_length=100)
    color: str | None = Field(default=None, max_length=20)
    description: str | None = Field(default=None, max_length=255)


class CustomerTagCreate(CustomerTagBase):
    pass


class CustomerTagUpdate(BaseSchema):
    name: str | None = Field(default=None, max_length=100)
    color: str | None = Field(default=None, max_length=20)
    description: str | None = Field(default=None, max_length=255)


class CustomerTagResponse(
    CustomerTagBase,
    TimestampSchema,
):
    pass


class CustomerTagListResponse(BaseSchema):
    total: int
    items: list[CustomerTagResponse]
    