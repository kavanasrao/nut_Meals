"""
Service layer for Blog Categories.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.blog_category import BlogCategory
from app.schemas.blog_category import (
    BlogCategoryCreate,
    BlogCategoryUpdate,
)


class BlogCategoryService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        data: BlogCategoryCreate,
    ) -> BlogCategory:
        category = BlogCategory(**data.model_dump())

        self.db.add(category)
        await self.db.commit()
        await self.db.refresh(category)

        return category

    async def get(
        self,
        category_id: UUID,
    ) -> BlogCategory | None:
        return await self.db.get(
            BlogCategory,
            category_id,
        )

    async def get_by_slug(
        self,
        slug: str,
    ) -> BlogCategory | None:
        result = await self.db.execute(
            select(BlogCategory).where(
                BlogCategory.slug == slug
            )
        )

        return result.scalar_one_or_none()

    async def list(self) -> list[BlogCategory]:
        result = await self.db.execute(
            select(BlogCategory).order_by(
                BlogCategory.name
            )
        )

        return list(result.scalars().all())

    async def update(
        self,
        category: BlogCategory,
        data: BlogCategoryUpdate,
    ) -> BlogCategory:
        updates = data.model_dump(exclude_unset=True)

        for key, value in updates.items():
            setattr(category, key, value)

        await self.db.commit()
        await self.db.refresh(category)

        return category

    async def delete(
        self,
        category: BlogCategory,
    ) -> None:
        await self.db.delete(category)
        await self.db.commit()