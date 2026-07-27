"""
Service layer for Blog Posts.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.blog_post import (
    BlogPost,
    BlogStatus,
)
from app.schemas.blog_post import (
    BlogPostCreate,
    BlogPostUpdate,
)


class BlogPostService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        data: BlogPostCreate,
    ) -> BlogPost:
        post = BlogPost(**data.model_dump())

        self.db.add(post)
        await self.db.commit()
        await self.db.refresh(post)

        return post

    async def get(
        self,
        post_id: UUID,
    ) -> BlogPost | None:
        return await self.db.get(
            BlogPost,
            post_id,
        )

    async def get_by_slug(
        self,
        slug: str,
    ) -> BlogPost | None:
        result = await self.db.execute(
            select(BlogPost).where(
                BlogPost.slug == slug
            )
        )

        return result.scalar_one_or_none()

    async def list(self) -> list[BlogPost]:
        result = await self.db.execute(
            select(BlogPost).order_by(
                BlogPost.created_at.desc()
            )
        )

        return list(result.scalars().all())

    async def list_published(self) -> list[BlogPost]:
        result = await self.db.execute(
            select(BlogPost)
            .where(
                BlogPost.status == BlogStatus.PUBLISHED
            )
            .order_by(
                BlogPost.published_at.desc()
            )
        )

        return list(result.scalars().all())

    async def update(
        self,
        post: BlogPost,
        data: BlogPostUpdate,
    ) -> BlogPost:
        updates = data.model_dump(exclude_unset=True)

        for key, value in updates.items():
            setattr(post, key, value)

        await self.db.commit()
        await self.db.refresh(post)

        return post

    async def publish(
        self,
        post: BlogPost,
    ) -> BlogPost:
        post.status = BlogStatus.PUBLISHED
        post.published_at = datetime.now(timezone.utc)

        await self.db.commit()
        await self.db.refresh(post)

        return post

    async def archive(
        self,
        post: BlogPost,
    ) -> BlogPost:
        post.status = BlogStatus.ARCHIVED

        await self.db.commit()
        await self.db.refresh(post)

        return post

    async def delete(
        self,
        post: BlogPost,
    ) -> None:
        await self.db.delete(post)
        await self.db.commit()