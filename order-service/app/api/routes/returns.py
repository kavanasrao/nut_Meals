"""
Returns API routes.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db

from app.schemas.returns import (
    ReturnCreate,
    ReturnOut,
)

from app.services.return_services import ReturnService

router = APIRouter(
    prefix="/returns",
    tags=["Returns"],
)


# ==========================================================
# Create Return
# ==========================================================

@router.post(
    "/",
    response_model=ReturnOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_return(
    body: ReturnCreate,
    db: AsyncSession = Depends(get_db),
):

    service = ReturnService(db)

    result = await service.create_return(body)

    return result


# ==========================================================
# Get Return
# ==========================================================

@router.get(
    "/{return_id}",
    response_model=ReturnOut,
)
async def get_return(
    return_id: UUID,
    db: AsyncSession = Depends(get_db),
):

    service = ReturnService(db)

    result = await service.get_return(return_id)

    if result is None:

        raise HTTPException(
            status_code=404,
            detail="Return not found",
        )

    return result


# ==========================================================
# Approve
# ==========================================================

@router.put(
    "/{return_id}/approve",
    response_model=ReturnOut,
)
async def approve_return(
    return_id: UUID,
    db: AsyncSession = Depends(get_db),
):

    service = ReturnService(db)

    request = await service.get_return(return_id)

    if request is None:

        raise HTTPException(
            status_code=404,
            detail="Return not found",
        )

    return await service.approve_return(request)


# ==========================================================
# Reject
# ==========================================================

@router.put(
    "/{return_id}/reject",
    response_model=ReturnOut,
)
async def reject_return(
    return_id: UUID,
    db: AsyncSession = Depends(get_db),
):

    service = ReturnService(db)

    request = await service.get_return(return_id)

    if request is None:

        raise HTTPException(
            status_code=404,
            detail="Return not found",
        )

    return await service.reject_return(request)


# ==========================================================
# Complete
# ==========================================================

@router.put(
    "/{return_id}/complete",
    response_model=ReturnOut,
)
async def complete_return(
    return_id: UUID,
    db: AsyncSession = Depends(get_db),
):

    service = ReturnService(db)

    request = await service.get_return(return_id)

    if request is None:

        raise HTTPException(
            status_code=404,
            detail="Return not found",
        )

    return await service.complete_return(request)