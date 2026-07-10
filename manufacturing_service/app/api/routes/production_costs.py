"""
Production Cost API routes.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.schemas.production_cost import (
    ProductionCostCreate,
    ProductionCostOut,
)
from app.services.production_cost_service import (
    ProductionCostService,
)

router = APIRouter(
    prefix="/production-costs",
    tags=["Production Costs"],
)


# ==========================================================
# CREATE
# ==========================================================

@router.post(
    "/",
    response_model=ProductionCostOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_cost(
    body: ProductionCostCreate,
    db: AsyncSession = Depends(get_db),
):

    service = ProductionCostService(db)

    return await service.create(body)


# ==========================================================
# LIST
# ==========================================================

@router.get(
    "/",
    response_model=list[ProductionCostOut],
)
async def list_costs(
    db: AsyncSession = Depends(get_db),
):

    service = ProductionCostService(db)

    return await service.list()


# ==========================================================
# GET
# ==========================================================

@router.get(
    "/{cost_id}",
    response_model=ProductionCostOut,
)
async def get_cost(
    cost_id: UUID,
    db: AsyncSession = Depends(get_db),
):

    service = ProductionCostService(db)

    cost = await service.get(cost_id)

    if cost is None:
        raise HTTPException(
            status_code=404,
            detail="Production cost not found",
        )

    return cost


# ==========================================================
# GET BY BATCH
# ==========================================================

@router.get(
    "/batch/{batch_id}",
    response_model=ProductionCostOut,
)
async def get_batch_cost(
    batch_id: UUID,
    db: AsyncSession = Depends(get_db),
):

    service = ProductionCostService(db)

    cost = await service.get_by_batch(batch_id)

    if cost is None:
        raise HTTPException(
            status_code=404,
            detail="Production cost not found",
        )

    return cost


# ==========================================================
# COST PER UNIT
# ==========================================================

@router.get(
    "/batch/{batch_id}/cost-per-unit",
)
async def cost_per_unit(
    batch_id: UUID,
    db: AsyncSession = Depends(get_db),
):

    service = ProductionCostService(db)

    cost = await service.cost_per_unit(batch_id)

    return {
        "batch_id": batch_id,
        "cost_per_unit": cost,
    }


# ==========================================================
# DELETE
# ==========================================================

@router.delete(
    "/{cost_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_cost(
    cost_id: UUID,
    db: AsyncSession = Depends(get_db),
):

    service = ProductionCostService(db)

    cost = await service.get(cost_id)

    if cost is None:
        raise HTTPException(
            status_code=404,
            detail="Production cost not found",
        )

    await service.delete(cost)

