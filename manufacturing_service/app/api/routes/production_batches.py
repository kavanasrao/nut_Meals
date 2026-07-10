"""
Production Batch API routes.
"""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.schemas.production_batch import (
    ProductionBatchCreate,
    ProductionBatchOut,
)
from app.services.production_batch_service import ProductionBatchService

router = APIRouter(
    prefix="/production-batches",
    tags=["Production Batches"],
)


# ==========================================================
# CREATE
# ==========================================================

@router.post(
    "/",
    response_model=ProductionBatchOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_batch(
    body: ProductionBatchCreate,
    db: AsyncSession = Depends(get_db),
):

    service = ProductionBatchService(db)

    return await service.create(body)


# ==========================================================
# LIST
# ==========================================================

@router.get(
    "/",
    response_model=list[ProductionBatchOut],
)
async def list_batches(
    db: AsyncSession = Depends(get_db),
):

    service = ProductionBatchService(db)

    return await service.list()


# ==========================================================
# GET
# ==========================================================

@router.get(
    "/{batch_id}",
    response_model=ProductionBatchOut,
)
async def get_batch(
    batch_id: UUID,
    db: AsyncSession = Depends(get_db),
):

    service = ProductionBatchService(db)

    batch = await service.get(batch_id)

    if batch is None:
        raise HTTPException(
            status_code=404,
            detail="Production batch not found",
        )

    return batch


# ==========================================================
# START
# ==========================================================

@router.put(
    "/{batch_id}/start",
    response_model=ProductionBatchOut,
)
async def start_batch(
    batch_id: UUID,
    db: AsyncSession = Depends(get_db),
):

    service = ProductionBatchService(db)

    batch = await service.get(batch_id)

    if batch is None:
        raise HTTPException(
            status_code=404,
            detail="Production batch not found",
        )

    return await service.start_batch(batch)


# ==========================================================
# COMPLETE
# ==========================================================

@router.put(
    "/{batch_id}/complete",
    response_model=ProductionBatchOut,
)
async def complete_batch(
    batch_id: UUID,
    produced_quantity: Decimal,
    db: AsyncSession = Depends(get_db),
):

    service = ProductionBatchService(db)

    batch = await service.get(batch_id)

    if batch is None:
        raise HTTPException(
            status_code=404,
            detail="Production batch not found",
        )

    return await service.complete_batch(
        batch,
        produced_quantity,
    )


# ==========================================================
# CANCEL
# ==========================================================

@router.put(
    "/{batch_id}/cancel",
    response_model=ProductionBatchOut,
)
async def cancel_batch(
    batch_id: UUID,
    db: AsyncSession = Depends(get_db),
):

    service = ProductionBatchService(db)

    batch = await service.get(batch_id)

    if batch is None:
        raise HTTPException(
            status_code=404,
            detail="Production batch not found",
        )

    return await service.cancel_batch(batch)
