from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.database import get_db
from app.repositories.customer_profile_repository import CustomerProfileRepository
from app.schema.customer_profile import (
    CustomerProfileCreate,
    CustomerProfileResponse,
    CustomerProfileUpdate,
)
from app.services.customer_profile_service import CustomerProfileService

router = APIRouter(
    prefix="/customers",
    tags=["Customer Profiles"],
)


def get_service(
    db: AsyncSession = Depends(get_db),
) -> CustomerProfileService:
    repository = CustomerProfileRepository(db)
    return CustomerProfileService(repository)


@router.post(
    "/",
    response_model=CustomerProfileResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_customer(
    payload: CustomerProfileCreate,
    service: CustomerProfileService = Depends(get_service),
):
    return await service.create_customer(payload)


@router.get(
    "/{customer_id}",
    response_model=CustomerProfileResponse,
)
async def get_customer(
    customer_id: UUID,
    service: CustomerProfileService = Depends(get_service),
):
    customer = await service.get_customer(customer_id)

    if customer is None:
        raise HTTPException(
            status_code=404,
            detail="Customer not found",
        )

    return customer


@router.get("/")
async def list_customers(
    skip: int = 0,
    limit: int = 100,
    service: CustomerProfileService = Depends(get_service),
):
    return await service.list_customers(skip, limit)


@router.put(
    "/{customer_id}",
    response_model=CustomerProfileResponse,
)
async def update_customer(
    customer_id: UUID,
    payload: CustomerProfileUpdate,
    service: CustomerProfileService = Depends(get_service),
):
    customer = await service.update_customer(
        customer_id,
        payload,
    )

    if customer is None:
        raise HTTPException(
            status_code=404,
            detail="Customer not found",
        )

    return customer


@router.delete("/{customer_id}")
async def delete_customer(
    customer_id: UUID,
    service: CustomerProfileService = Depends(get_service),
):
    deleted = await service.delete_customer(customer_id)

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="Customer not found",
        )

    return {"message": "Customer deleted successfully"}