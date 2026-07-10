from uuid import UUID

from pydantic import Field

from app.schemas.base import BaseSchema, TimestampSchema


class CustomerAuditBase(BaseSchema):
    customer_id: UUID

    action: str = Field(..., max_length=100)

    entity_name: str = Field(..., max_length=100)

    entity_id: UUID | None = None

    performed_by: UUID

    ip_address: str | None = Field(
        default=None,
        max_length=45,
    )

    user_agent: str | None = Field(
        default=None,
        max_length=500,
    )

    old_data: dict | None = None

    new_data: dict | None = None


class CustomerAuditCreate(CustomerAuditBase):
    pass


class CustomerAuditUpdate(BaseSchema):
    action: str | None = Field(default=None, max_length=100)
    entity_name: str | None = Field(default=None, max_length=100)
    entity_id: UUID | None = None
    performed_by: UUID | None = None
    ip_address: str | None = Field(default=None, max_length=45)
    user_agent: str | None = Field(default=None, max_length=500)
    old_data: dict | None = None
    new_data: dict | None = None


class CustomerAuditResponse(
    CustomerAuditBase,
    TimestampSchema,
):
    pass


class CustomerAuditListResponse(BaseSchema):
    total: int
    items: list[CustomerAuditResponse]