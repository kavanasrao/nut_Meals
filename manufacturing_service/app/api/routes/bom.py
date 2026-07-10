"""
Bill of Materials (BOM) API routes.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.schemas.bom import BOMCreate, BOMOut
from app.services.bom_service import BOMService

router = APIRouter(
    prefix="/boms",
    tags=["Bill Of Materials"],
)


# ==========================================================
# CREATE
# ==========================================================

@router.post(
    "/",
    response_model=BOMOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_bom(
    body: BOMCreate,
    db: AsyncSession = Depends(get_db),
):

    service = BOMService(db)

    return await service.create(body)


# ==========================================================
# GET
# ==========================================================

@router.get(
    "/{bom_id}",
    response_model=BOMOut,
)
async def get_bom(
    bom_id: UUID,
    db: AsyncSession = Depends(get_db),
):

    service = BOMService(db)

    bom = await service.get(bom_id)

    if bom is None:
        raise HTTPException(
            status_code=404,
            detail="BOM not found",
        )

    return bom


# ==========================================================
# LIST
# ==========================================================

@router.get(
    "/",
    response_model=list[BOMOut],
)
async def list_boms(
    db: AsyncSession = Depends(get_db),
):

    service = BOMService(db)

    return await service.list()


# ==========================================================
# ACTIVATE
# ==========================================================

@router.put(
    "/{bom_id}/activate",
    response_model=BOMOut,
)
async def activate_bom(
    bom_id: UUID,
    db: AsyncSession = Depends(get_db),
):

    service = BOMService(db)

    bom = await service.get(bom_id)

    if bom is None:
        raise HTTPException(
            status_code=404,
            detail="BOM not found",
        )

    return await service.activate(bom)


# ==========================================================
# DEACTIVATE
# ==========================================================

@router.put(
    "/{bom_id}/deactivate",
    response_model=BOMOut,
)
async def deactivate_bom(
    bom_id: UUID,
    db: AsyncSession = Depends(get_db),
):

    service = BOMService(db)

    bom = await service.get(bom_id)

    if bom is None:
        raise HTTPException(
            status_code=404,
            detail="BOM not found",
        )

    return await service.deactivate(bom)


# ==========================================================
# DELETE
# ==========================================================

@router.delete(
    "/{bom_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_bom(
    bom_id: UUID,
    db: AsyncSession = Depends(get_db),
):

    service = BOMService(db)

    bom = await service.get(bom_id)

    if bom is None:
        raise HTTPException(
            status_code=404,
            detail="BOM not found",
        )

    await service.delete(bom)
