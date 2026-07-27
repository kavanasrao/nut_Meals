"""
Recipe service.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.recipe import Recipe, RecipeStatus
from app.schemas.recipe import RecipeCreate, RecipeUpdate


class RecipeService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_recipe(self, recipe_in: RecipeCreate) -> Recipe:
        recipe = Recipe(**recipe_in.model_dump())

        self.db.add(recipe)
        await self.db.commit()
        await self.db.refresh(recipe)

        return recipe

    async def get_recipe(self, recipe_id: UUID) -> Recipe | None:
        result = await self.db.execute(
            select(Recipe).where(Recipe.id == recipe_id)
        )
        return result.scalar_one_or_none()

    async def get_by_code(self, recipe_code: str) -> Recipe | None:
        result = await self.db.execute(
            select(Recipe).where(
                Recipe.recipe_code == recipe_code
            )
        )
        return result.scalar_one_or_none()

    async def list_recipes(self) -> list[Recipe]:
        result = await self.db.execute(
            select(Recipe).order_by(Recipe.created_at.desc())
        )
        return list(result.scalars().all())

    async def list_by_status(
        self,
        status: RecipeStatus,
    ) -> list[Recipe]:
        result = await self.db.execute(
            select(Recipe).where(
                Recipe.status == status
            )
        )
        return list(result.scalars().all())

    async def update_recipe(
        self,
        recipe_id: UUID,
        recipe_in: RecipeUpdate,
    ) -> Recipe | None:

        recipe = await self.get_recipe(recipe_id)

        if recipe is None:
            return None

        update_data = recipe_in.model_dump(exclude_unset=True)

        for key, value in update_data.items():
            setattr(recipe, key, value)

        await self.db.commit()
        await self.db.refresh(recipe)

        return recipe

    async def activate_recipe(
        self,
        recipe_id: UUID,
    ) -> Recipe | None:

        recipe = await self.get_recipe(recipe_id)

        if recipe is None:
            return None

        recipe.status = RecipeStatus.ACTIVE

        await self.db.commit()
        await self.db.refresh(recipe)

        return recipe

    async def deactivate_recipe(
        self,
        recipe_id: UUID,
    ) -> Recipe | None:

        recipe = await self.get_recipe(recipe_id)

        if recipe is None:
            return None

        recipe.status = RecipeStatus.INACTIVE

        await self.db.commit()
        await self.db.refresh(recipe)

        return recipe

    async def archive_recipe(
        self,
        recipe_id: UUID,
    ) -> Recipe | None:

        recipe = await self.get_recipe(recipe_id)

        if recipe is None:
            return None

        recipe.status = RecipeStatus.ARCHIVED

        await self.db.commit()
        await self.db.refresh(recipe)

        return recipe

    async def delete_recipe(
        self,
        recipe_id: UUID,
    ) -> bool:

        recipe = await self.get_recipe(recipe_id)

        if recipe is None:
            return False

        await self.db.delete(recipe)
        await self.db.commit()

        return True

    async def total_recipes(self) -> int:
        result = await self.db.execute(
            select(Recipe)
        )

        return len(result.scalars().all())