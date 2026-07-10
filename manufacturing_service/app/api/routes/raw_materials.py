"""
Raw Material API routes.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.schemas.raw_material import (
    RawMaterialCreate,
    RawMaterialOut,
    RawMaterialUpdate,
)
from app.services.raw_material_service import RawMaterialService

router = APIRouter(
    prefix="/raw-materials",
    tags=["Raw Materials"],
)


@router.post(
    "/",
    response_model=RawMaterialOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_raw_material(
    body: RawMaterialCreate,
    db: AsyncSession = Depends(get_db),
):
    service = RawMaterialService(db)
    return await service.create(body)


@router.get(
    "/",
    response_model=list[RawMaterialOut],
)
async def list_raw_materials(
    db: AsyncSession = Depends(get_db),
):
    service = RawMaterialService(db)
    return await service.list()


@router.get(
    "/{material_id}",
    response_model=RawMaterialOut,
)
async def get_raw_material(
    material_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    service = RawMaterialService(db)

    material = await service.get(material_id)

    if material is None:
        raise HTTPException(
            status_code=404,
            detail="Raw material not found",
        )

    return material


@router.put(
    "/{material_id}",
    response_model=RawMaterialOut,
)
async def update_raw_material(
    material_id: UUID,
    body: RawMaterialUpdate,
    db: AsyncSession = Depends(get_db),
):
    service = RawMaterialService(db)

    material = await service.get(material_id)

    if material is None:
        raise HTTPException(
            status_code=404,
            detail="Raw material not found",
        )

    return await service.update(material, body)


@router.delete(
    "/{material_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_raw_material(
    material_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    service = RawMaterialService(db)

    material = await service.get(material_id)

    if material is None:
        raise HTTPException(
            status_code=404,
            detail="Raw material not found",
        )

    await service.delete(material)

