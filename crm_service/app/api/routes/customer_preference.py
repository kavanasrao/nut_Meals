from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.database import get_db
from app.repositories.customer_preference_repository import (
    CustomerPreferenceRepository,
)
from app.schema.customer_preference import (
    CustomerPreferenceCreate,
    CustomerPreferenceResponse,
    CustomerPreferenceUpdate,
)
from app.services.customer_preference_service import (
    CustomerPreferenceService,
)

router = APIRouter(
    prefix="/customer-preferences",
    tags=["Customer Preferences"],
)


def get_service(
    db: AsyncSession = Depends(get_db),
) -> CustomerPreferenceService:
    repository = CustomerPreferenceRepository(db)
    return CustomerPreferenceService(repository)


@router.post(
    "/",
    response_model=CustomerPreferenceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_preference(
    payload: CustomerPreferenceCreate,
    service: CustomerPreferenceService = Depends(get_service),
):
    return await service.create_preference(payload)


@router.get(
    "/{preference_id}",
    response_model=CustomerPreferenceResponse,
)
async def get_preference(
    preference_id: UUID,
    service: CustomerPreferenceService = Depends(get_service),
):
    preference = await service.get_preference(preference_id)

    if preference is None:
        raise HTTPException(
            status_code=404,
            detail="Customer preference not found",
        )

    return preference


@router.get("/customer/{customer_id}")
async def get_customer_preference(
    customer_id: UUID,
    service: CustomerPreferenceService = Depends(get_service),
):
    return await service.get_customer_preference(customer_id)


@router.put(
    "/{preference_id}",
    response_model=CustomerPreferenceResponse,
)
async def update_preference(
    preference_id: UUID,
    payload: CustomerPreferenceUpdate,
    service: CustomerPreferenceService = Depends(get_service),
):
    preference = await service.update_preference(
        preference_id,
        payload,
    )

    if preference is None:
        raise HTTPException(
            status_code=404,
            detail="Customer preference not found",
        )

    return preference


@router.patch("/{customer_id}/enable-notifications")
async def enable_notifications(
    customer_id: UUID,
    service: CustomerPreferenceService = Depends(get_service),
):
    preference = await service.enable_notifications(customer_id)

    if preference is None:
        raise HTTPException(
            status_code=404,
            detail="Customer preference not found",
        )

    return preference


@router.patch("/{customer_id}/disable-notifications")
async def disable_notifications(
    customer_id: UUID,
    service: CustomerPreferenceService = Depends(get_service),
):
    preference = await service.disable_notifications(customer_id)

    if preference is None:
        raise HTTPException(
            status_code=404,
            detail="Customer preference not found",
        )

    return preference


@router.delete("/{preference_id}")
async def delete_preference(
    preference_id: UUID,
    service: CustomerPreferenceService = Depends(get_service),
):
    deleted = await service.delete_preference(preference_id)

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="Customer preference not found",
        )

    return {
        "message": "Customer preference deleted successfully",
    }