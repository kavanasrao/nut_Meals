from uuid import UUID

from app.schemas.base import BaseSchema, TimestampSchema


class CustomerNoteBase(BaseSchema):
    customer_id: UUID
    created_by: UUID

    note: str

    is_internal: bool = True


class CustomerNoteCreate(CustomerNoteBase):
    pass


class CustomerNoteUpdate(BaseSchema):
    note: str | None = None
    is_internal: bool | None = None


class CustomerNoteResponse(
    CustomerNoteBase,
    TimestampSchema,
):
    pass


class CustomerNoteListResponse(BaseSchema):
    total: int
    items: list[CustomerNoteResponse]
    