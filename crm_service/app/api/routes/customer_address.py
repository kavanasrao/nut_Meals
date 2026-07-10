from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.database import get_db
from app.repositories.customer_address_repository import (
    CustomerAddressRepository,
)
from app.schema.customer_address import (
    CustomerAddressCreate,
    CustomerAddressResponse,
    CustomerAddressUpdate,
)
from app.services.customer_address_service import (
    CustomerAddressService,
)

router = APIRouter(
    prefix="/customer-addresses",
    tags=["Customer Addresses"],
)


def get_service(
    db: AsyncSession = Depends(get_db),
) -> CustomerAddressService:
    repository = CustomerAddressRepository(db)
    return CustomerAddressService(repository)


@router.post(
    "/",
    response_model=CustomerAddressResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_address(
    payload: CustomerAddressCreate,
    service: CustomerAddressService = Depends(get_service),
):
    return await service.create_address(payload)


@router.get(
    "/{address_id}",
    response_model=CustomerAddressResponse,
)
async def get_address(
    address_id: UUID,
    service: CustomerAddressService = Depends(get_service),
):
    address = await service.get_address(address_id)

    if address is None:
        raise HTTPException(
            status_code=404,
            detail="Address not found",
        )

    return address


@router.get("/customer/{customer_id}")
async def get_customer_addresses(
    customer_id: UUID,
    service: CustomerAddressService = Depends(get_service),
):
    return await service.get_customer_addresses(customer_id)


@router.put(
    "/{address_id}",
    response_model=CustomerAddressResponse,
)
async def update_address(
    address_id: UUID,
    payload: CustomerAddressUpdate,
    service: CustomerAddressService = Depends(get_service),
):
    address = await service.update_address(address_id, payload)

    if address is None:
        raise HTTPException(
            status_code=404,
            detail="Address not found",
        )

    return address


@router.delete("/{address_id}")
async def delete_address(
    address_id: UUID,
    service: CustomerAddressService = Depends(get_service),
):
    deleted = await service.delete_address(address_id)

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="Address not found",
        )

    return {"message": "Address deleted successfully"}