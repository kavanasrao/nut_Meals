"""
Recipe Item API routes.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.recipe_item import (
    RecipeItemCreate,
    RecipeItemResponse,
    RecipeItemUpdate,
)
from app.services.recipe_item_service import RecipeItemService

router = APIRouter(
    prefix="/recipe-items",
    tags=["Recipe Items"],
)


@router.post(
    "/",
    response_model=RecipeItemResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_recipe_item(
    item: RecipeItemCreate,
    db: AsyncSession = Depends(get_db),
):
    service = RecipeItemService(db)
    return await service.create_recipe_item(item)


@router.get(
    "/recipe/{recipe_id}",
    response_model=list[RecipeItemResponse],
)
async def list_recipe_items(
    recipe_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    service = RecipeItemService(db)
    return await service.list_recipe_items(recipe_id)


@router.get(
    "/{item_id}",
    response_model=RecipeItemResponse,
)
async def get_recipe_item(
    item_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    service = RecipeItemService(db)

    item = await service.get_recipe_item(item_id)

    if item is None:
        raise HTTPException(
            status_code=404,
            detail="Recipe item not found",
        )

    return item


@router.put(
    "/{item_id}",
    response_model=RecipeItemResponse,
)
async def update_recipe_item(
    item_id: UUID,
    item: RecipeItemUpdate,
    db: AsyncSession = Depends(get_db),
):
    service = RecipeItemService(db)

    updated = await service.update_recipe_item(
        item_id,
        item,
    )

    if updated is None:
        raise HTTPException(
            status_code=404,
            detail="Recipe item not found",
        )

    return updated


@router.delete(
    "/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_recipe_item(
    item_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    service = RecipeItemService(db)

    deleted = await service.delete_recipe_item(item_id)

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="Recipe item not found",
        )