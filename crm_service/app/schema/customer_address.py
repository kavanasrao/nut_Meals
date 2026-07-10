from uuid import UUID

from pydantic import Field

from app.schemas.base import BaseSchema, TimestampSchema


class CustomerAddressBase(BaseSchema):
    customer_id: UUID

    address_type: str = Field(..., max_length=30)

    full_name: str = Field(..., max_length=100)

    phone_number: str = Field(..., max_length=20)

    address_line1: str = Field(..., max_length=255)
    address_line2: str | None = Field(default=None, max_length=255)

    city: str = Field(..., max_length=100)
    state: str = Field(..., max_length=100)
    country: str = Field(..., max_length=100)
    postal_code: str = Field(..., max_length=20)

    landmark: str | None = None

    is_default: bool = False


class CustomerAddressCreate(CustomerAddressBase):
    pass


class CustomerAddressUpdate(BaseSchema):
    address_type: str | None = Field(default=None, max_length=30)
    full_name: str | None = Field(default=None, max_length=100)
    phone_number: str | None = Field(default=None, max_length=20)

    address_line1: str | None = Field(default=None, max_length=255)
    address_line2: str | None = Field(default=None, max_length=255)

    city: str | None = Field(default=None, max_length=100)
    state: str | None = Field(default=None, max_length=100)
    country: str | None = Field(default=None, max_length=100)
    postal_code: str | None = Field(default=None, max_length=20)

    landmark: str | None = None
    is_default: bool | None = None


class CustomerAddressResponse(
    CustomerAddressBase,
    TimestampSchema,
):
    pass


class CustomerAddressListResponse(BaseSchema):
    total: int
    items: list[CustomerAddressResponse]