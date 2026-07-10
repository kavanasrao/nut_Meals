from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.database import get_db
from app.repositories.customer_interaction_repository import (
    CustomerInteractionRepository,
)
from app.schema.customer_interaction import (
    CustomerInteractionCreate,
    CustomerInteractionResponse,
    CustomerInteractionUpdate,
)
from app.services.customer_interaction_service import (
    CustomerInteractionService,
)

router = APIRouter(
    prefix="/customer-interactions",
    tags=["Customer Interactions"],
)


def get_service(
    db: AsyncSession = Depends(get_db),
) -> CustomerInteractionService:
    repository = CustomerInteractionRepository(db)
    return CustomerInteractionService(repository)


@router.post(
    "/",
    response_model=CustomerInteractionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_interaction(
    payload: CustomerInteractionCreate,
    service: CustomerInteractionService = Depends(get_service),
):
    return await service.create_interaction(payload)


@router.get(
    "/{interaction_id}",
    response_model=CustomerInteractionResponse,
)
async def get_interaction(
    interaction_id: UUID,
    service: CustomerInteractionService = Depends(get_service),
):
    interaction = await service.get_interaction(interaction_id)

    if interaction is None:
        raise HTTPException(
            status_code=404,
            detail="Customer interaction not found",
        )

    return interaction


@router.get("/customer/{customer_id}")
async def get_customer_interactions(
    customer_id: UUID,
    service: CustomerInteractionService = Depends(get_service),
):
    return await service.get_customer_interactions(customer_id)


@router.get("/customer/{customer_id}/type/{interaction_type}")
async def get_interactions_by_type(
    customer_id: UUID,
    interaction_type: str,
    service: CustomerInteractionService = Depends(get_service),
):
    return await service.get_interactions_by_type(
        customer_id,
        interaction_type,
    )


@router.get("/staff/{staff_id}")
async def get_staff_interactions(
    staff_id: UUID,
    service: CustomerInteractionService = Depends(get_service),
):
    return await service.get_staff_interactions(staff_id)


@router.put(
    "/{interaction_id}",
    response_model=CustomerInteractionResponse,
)
async def update_interaction(
    interaction_id: UUID,
    payload: CustomerInteractionUpdate,
    service: CustomerInteractionService = Depends(get_service),
):
    interaction = await service.update_interaction(
        interaction_id,
        payload,
    )

    if interaction is None:
        raise HTTPException(
            status_code=404,
            detail="Customer interaction not found",
        )

    return interaction


@router.delete("/{interaction_id}")
async def delete_interaction(
    interaction_id: UUID,
    service: CustomerInteractionService = Depends(get_service),
):
    deleted = await service.delete_interaction(interaction_id)

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="Customer interaction not found",
        )

    return {
        "message": "Customer interaction deleted successfully",
    }