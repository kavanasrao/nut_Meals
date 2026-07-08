"""Delivery Service — REST API routes.

GET  /api/v1/delivery/options?location={lat,lon}  — available delivery methods + ETA
GET  /api/v1/delivery/{order_id}                  — delivery assignment for an order
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.models.delivery import DeliveryAssignment
from app.schemas.delivery import DeliveryAssignmentOut, DeliveryOptionsResponse
from app.services.delivery_service import DeliveryService

router = APIRouter(prefix="/delivery", tags=["delivery"])


@router.get(
    "/options",
    response_model=DeliveryOptionsResponse,
    summary="Get available delivery options for a location",
)
async def get_delivery_options(
    location: str = Query(
        ...,
        description="Comma-separated lat,lon. Example: 12.9716,77.5946",
        example="12.9716,77.5946",
    ),
    db: AsyncSession = Depends(get_db),
) -> DeliveryOptionsResponse:
    """
    Returns available delivery methods filtered by:
    - User location (within delivery radius)
    - Service operating hours
    - ETA calculated using Haversine distance from restaurant
    """
    svc = DeliveryService(db)
    return await svc.get_delivery_options(location)


@router.get(
    "/{order_id}",
    response_model=DeliveryAssignmentOut,
    summary="Get delivery assignment for an order",
)
async def get_delivery_assignment(
    order_id: str,
    db: AsyncSession = Depends(get_db),
) -> DeliveryAssignmentOut:
    result = await db.execute(
        select(DeliveryAssignment).where(DeliveryAssignment.order_id == order_id)
    )
    assignment = result.scalar_one_or_none()
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Delivery assignment not found for this order",
        )
    return DeliveryAssignmentOut.model_validate(
        {
            **{c.key: getattr(assignment, c.key) for c in assignment.__mapper__.columns},
            "created_at": assignment.created_at.isoformat(),
            "updated_at": assignment.updated_at.isoformat(),
        }
    )
