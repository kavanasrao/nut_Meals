from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.database import get_db
from app.repositories.customer_segment_repository import (
    CustomerSegmentRepository,
)
from app.schema.customer_segment import (
    CustomerSegmentCreate,
    CustomerSegmentResponse,
    CustomerSegmentUpdate,
)
from app.services.customer_segment_service import (
    CustomerSegmentService,
)

router = APIRouter(
    prefix="/customer-segments",
    tags=["Customer Segments"],
)


def get_service(
    db: AsyncSession = Depends(get_db),
) -> CustomerSegmentService:
    repository = CustomerSegmentRepository(db)
    return CustomerSegmentService(repository)


@router.post(
    "/",
    response_model=CustomerSegmentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_segment(
    payload: CustomerSegmentCreate,
    service: CustomerSegmentService = Depends(get_service),
):
    return await service.create_segment(payload)


@router.get(
    "/{segment_id}",
    response_model=CustomerSegmentResponse,
)
async def get_segment(
    segment_id: UUID,
    service: CustomerSegmentService = Depends(get_service),
):
    segment = await service.get_segment(segment_id)

    if segment is None:
        raise HTTPException(
            status_code=404,
            detail="Segment not found",
        )

    return segment


@router.get("/customer/{customer_id}")
async def get_customer_segments(
    customer_id: UUID,
    service: CustomerSegmentService = Depends(get_service),
):
    return await service.get_customer_segments(customer_id)


@router.get("/dynamic")
async def get_dynamic_segments(
    service: CustomerSegmentService = Depends(get_service),
):
    return await service.get_dynamic_segments()


@router.put(
    "/{segment_id}",
    response_model=CustomerSegmentResponse,
)
async def update_segment(
    segment_id: UUID,
    payload: CustomerSegmentUpdate,
    service: CustomerSegmentService = Depends(get_service),
):
    segment = await service.update_segment(
        segment_id,
        payload,
    )

    if segment is None:
        raise HTTPException(
            status_code=404,
            detail="Segment not found",
        )

    return segment


@router.delete("/{segment_id}")
async def delete_segment(
    segment_id: UUID,
    service: CustomerSegmentService = Depends(get_service),
):
    deleted = await service.delete_segment(segment_id)

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="Segment not found",
        )

    return {
        "message": "Segment deleted successfully",
    }