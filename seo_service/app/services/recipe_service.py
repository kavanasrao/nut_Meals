"""
Service layer for Recipe Content.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.recipe import (
    Recipe,
    RecipeStatus,
)
from app.schemas.recipe import (
    RecipeCreate,
    RecipeUpdate,
)


class RecipeService:
    def __init__(
        self,
        db: AsyncSession,
    ):
        self.db = db

    async def create(
        self,
        data: RecipeCreate,
    ) -> Recipe:
        recipe = Recipe(
            **data.model_dump()
        )

        self.db.add(recipe)

        await self.db.commit()
        await self.db.refresh(recipe)

        return recipe

    async def get(
        self,
        recipe_id: UUID,
    ) -> Recipe | None:
        return await self.db.get(
            Recipe,
            recipe_id,
        )

    async def get_by_slug(
        self,
        slug: str,
    ) -> Recipe | None:
        result = await self.db.execute(
            select(Recipe).where(
                Recipe.slug == slug
            )
        )

        return result.scalar_one_or_none()

    async def list(self) -> list[Recipe]:
        result = await self.db.execute(
            select(Recipe).order_by(
                Recipe.created_at.desc()
            )
        )

        return list(
            result.scalars().all()
        )

    async def list_published(
        self,
    ) -> list[Recipe]:
        result = await self.db.execute(
            select(Recipe)
            .where(
                Recipe.status == RecipeStatus.PUBLISHED
            )
            .order_by(
                Recipe.published_at.desc()
            )
        )

        return list(
            result.scalars().all()
        )

    async def update(
        self,
        recipe: Recipe,
        data: RecipeUpdate,
    ) -> Recipe:
        updates = data.model_dump(
            exclude_unset=True
        )

        for key, value in updates.items():
            setattr(
                recipe,
                key,
                value,
            )

        await self.db.commit()
        await self.db.refresh(recipe)

        return recipe

    async def publish(
        self,
        recipe: Recipe,
    ) -> Recipe:
        recipe.status = RecipeStatus.PUBLISHED
        recipe.published_at = datetime.now(
            timezone.utc
        )

        await self.db.commit()
        await self.db.refresh(recipe)

        return recipe

    async def archive(
        self,
        recipe: Recipe,
    ) -> Recipe:
        recipe.status = RecipeStatus.ARCHIVED

        await self.db.commit()
        await self.db.refresh(recipe)

        return recipe

    async def delete(
        self,
        recipe: Recipe,
    ) -> None:
        await self.db.delete(recipe)
        await self.db.commit()