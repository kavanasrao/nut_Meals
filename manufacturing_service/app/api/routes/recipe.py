"""
Recipe API routes.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.schemas.recipe import (
    RecipeCreate,
    RecipeResponse,
    RecipeUpdate,
)
from app.services.recipe_service import RecipeService

router = APIRouter(
    prefix="/recipes",
    tags=["Recipe Management"],
)


@router.post(
    "/",
    response_model=RecipeResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_recipe(
    recipe: RecipeCreate,
    db: AsyncSession = Depends(get_db),
):
    service = RecipeService(db)
    return await service.create_recipe(recipe)


@router.get(
    "/",
    response_model=list[RecipeResponse],
)
async def list_recipes(
    db: AsyncSession = Depends(get_db),
):
    service = RecipeService(db)
    return await service.list_recipes()


@router.get(
    "/{recipe_id}",
    response_model=RecipeResponse,
)
async def get_recipe(
    recipe_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    service = RecipeService(db)

    recipe = await service.get_recipe(recipe_id)

    if recipe is None:
        raise HTTPException(
            status_code=404,
            detail="Recipe not found",
        )

    return recipe


@router.put(
    "/{recipe_id}",
    response_model=RecipeResponse,
)
async def update_recipe(
    recipe_id: UUID,
    recipe: RecipeUpdate,
    db: AsyncSession = Depends(get_db),
):
    service = RecipeService(db)

    updated = await service.update_recipe(
        recipe_id,
        recipe,
    )

    if updated is None:
        raise HTTPException(
            status_code=404,
            detail="Recipe not found",
        )

    return updated


@router.delete(
    "/{recipe_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_recipe(
    recipe_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    service = RecipeService(db)

    deleted = await service.delete_recipe(recipe_id)

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="Recipe not found",
        )


@router.patch(
    "/{recipe_id}/activate",
    response_model=RecipeResponse,
)
async def activate_recipe(
    recipe_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    service = RecipeService(db)

    recipe = await service.activate_recipe(recipe_id)

    if recipe is None:
        raise HTTPException(
            status_code=404,
            detail="Recipe not found",
        )

    return recipe


@router.patch(
    "/{recipe_id}/deactivate",
    response_model=RecipeResponse,
)
async def deactivate_recipe(
    recipe_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    service = RecipeService(db)

    recipe = await service.deactivate_recipe(recipe_id)

    if recipe is None:
        raise HTTPException(
            status_code=404,
            detail="Recipe not found",
        )

    return recipe


@router.patch(
    "/{recipe_id}/archive",
    response_model=RecipeResponse,
)
async def archive_recipe(
    recipe_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    service = RecipeService(db)

    recipe = await service.archive_recipe(recipe_id)

    if recipe is None:
        raise HTTPException(
            status_code=404,
            detail="Recipe not found",
        )

    return recipe