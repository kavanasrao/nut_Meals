from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.database import get_db
from app.repositories.customer_timeline_repository import (
    CustomerTimelineRepository,
)
from app.schema.customer_timeline import (
    CustomerTimelineCreate,
    CustomerTimelineResponse,
    CustomerTimelineUpdate,
)
from app.services.customer_timeline_service import (
    CustomerTimelineService,
)

router = APIRouter(
    prefix="/timeline",
    tags=["Customer Timeline"],
)


def get_service(
    db: AsyncSession = Depends(get_db),
) -> CustomerTimelineService:
    repository = CustomerTimelineRepository(db)
    return CustomerTimelineService(repository)


@router.post(
    "/",
    response_model=CustomerTimelineResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_event(
    payload: CustomerTimelineCreate,
    service: CustomerTimelineService = Depends(get_service),
):
    return await service.create_event(payload)


@router.get(
    "/{timeline_id}",
    response_model=CustomerTimelineResponse,
)
async def get_event(
    timeline_id: UUID,
    service: CustomerTimelineService = Depends(get_service),
):
    event = await service.get_event(timeline_id)

    if event is None:
        raise HTTPException(
            status_code=404,
            detail="Timeline event not found",
        )

    return event


@router.get("/customer/{customer_id}")
async def get_customer_timeline(
    customer_id: UUID,
    service: CustomerTimelineService = Depends(get_service),
):
    return await service.get_customer_timeline(customer_id)


@router.put(
    "/{timeline_id}",
    response_model=CustomerTimelineResponse,
)
async def update_event(
    timeline_id: UUID,
    payload: CustomerTimelineUpdate,
    service: CustomerTimelineService = Depends(get_service),
):
    event = await service.update_event(
        timeline_id,
        payload,
    )

    if event is None:
        raise HTTPException(
            status_code=404,
            detail="Timeline event not found",
        )

    return event


@router.delete("/{timeline_id}")
async def delete_event(
    timeline_id: UUID,
    service: CustomerTimelineService = Depends(get_service),
):
    deleted = await service.delete_event(timeline_id)

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="Timeline event not found",
        )

    return {"message": "Timeline event deleted successfully"}