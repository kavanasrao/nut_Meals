"""
API routes for Recipe Content.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.recipe import (
    RecipeCreate,
    RecipeOut,
    RecipeUpdate,
)
from app.services.recipe_service import (
    RecipeService,
)

router = APIRouter(
    prefix="/recipes",
    tags=["Recipes"],
)


# ==========================================================
# CREATE
# ==========================================================

@router.post(
    "",
    response_model=RecipeOut,
)
async def create_recipe(
    data: RecipeCreate,
    db: AsyncSession = Depends(get_db),
):
    service = RecipeService(db)

    return await service.create(data)


# ==========================================================
# LIST
# ==========================================================

@router.get(
    "",
    response_model=list[RecipeOut],
)
async def list_recipes(
    db: AsyncSession = Depends(get_db),
):
    service = RecipeService(db)

    return await service.list()


# ==========================================================
# LIST PUBLISHED
# ==========================================================

@router.get(
    "/published",
    response_model=list[RecipeOut],
)
async def list_published_recipes(
    db: AsyncSession = Depends(get_db),
):
    service = RecipeService(db)

    return await service.list_published()


# ==========================================================
# GET
# ==========================================================

@router.get(
    "/{recipe_id}",
    response_model=RecipeOut,
)
async def get_recipe(
    recipe_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    service = RecipeService(db)

    recipe = await service.get(recipe_id)

    if recipe is None:
        raise HTTPException(
            status_code=404,
            detail="Recipe not found.",
        )

    return recipe


# ==========================================================
# UPDATE
# ==========================================================

@router.put(
    "/{recipe_id}",
    response_model=RecipeOut,
)
async def update_recipe(
    recipe_id: UUID,
    data: RecipeUpdate,
    db: AsyncSession = Depends(get_db),
):
    service = RecipeService(db)

    recipe = await service.get(recipe_id)

    if recipe is None:
        raise HTTPException(
            status_code=404,
            detail="Recipe not found.",
        )

    return await service.update(
        recipe,
        data,
    )


# ==========================================================
# PUBLISH
# ==========================================================

@router.patch(
    "/{recipe_id}/publish",
    response_model=RecipeOut,
)
async def publish_recipe(
    recipe_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    service = RecipeService(db)

    recipe = await service.get(recipe_id)

    if recipe is None:
        raise HTTPException(
            status_code=404,
            detail="Recipe not found.",
        )

    return await service.publish(recipe)


# ==========================================================
# ARCHIVE
# ==========================================================

@router.patch(
    "/{recipe_id}/archive",
    response_model=RecipeOut,
)
async def archive_recipe(
    recipe_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    service = RecipeService(db)

    recipe = await service.get(recipe_id)

    if recipe is None:
        raise HTTPException(
            status_code=404,
            detail="Recipe not found.",
        )

    return await service.archive(recipe)


# ==========================================================
# DELETE
# ==========================================================

@router.delete(
    "/{recipe_id}",
    status_code=204,
)
async def delete_recipe(
    recipe_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    service = RecipeService(db)

    recipe = await service.get(recipe_id)

    if recipe is None:
        raise HTTPException(
            status_code=404,
            detail="Recipe not found.",
        )

    await service.delete(recipe)