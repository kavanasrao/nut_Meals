from uuid import UUID

from app.models.customer_address import CustomerAddress
from app.repositories.customer_address_repository import (
    CustomerAddressRepository,
)
from app.schemas.customer_address import (
    CustomerAddressCreate,
    CustomerAddressUpdate,
)


class CustomerAddressService:
    def __init__(
        self,
        repository: CustomerAddressRepository,
    ) -> None:
        self.repository = repository

    async def create_address(
        self,
        data: CustomerAddressCreate,
    ) -> CustomerAddress:
        address = CustomerAddress(**data.model_dump())
        return await self.repository.create(address)

    async def get_address(
        self,
        address_id: UUID,
    ) -> CustomerAddress | None:
        return await self.repository.get_by_id(address_id)

    async def get_customer_addresses(
        self,
        customer_id: UUID,
    ) -> list[CustomerAddress]:
        return await self.repository.get_by_customer_id(customer_id)

    async def get_default_address(
        self,
        customer_id: UUID,
    ) -> CustomerAddress | None:
        return await self.repository.get_default_address(customer_id)

    async def update_address(
        self,
        address_id: UUID,
        data: CustomerAddressUpdate,
    ) -> CustomerAddress | None:
        address = await self.repository.get_by_id(address_id)

        if address is None:
            return None

        return await self.repository.update(
            address,
            data.model_dump(exclude_unset=True),
        )

    async def set_default_address(
        self,
        customer_id: UUID,
        address_id: UUID,
    ) -> CustomerAddress | None:
        return await self.repository.set_default_address(
            customer_id,
            address_id,
        )

    async def delete_address(
        self,
        address_id: UUID,
    ) -> bool:
        return await self.repository.soft_delete(address_id)