"""
API routes for Blog Posts.
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
from app.schemas.blog_post import (
    BlogPostCreate,
    BlogPostOut,
    BlogPostUpdate,
)
from app.services.blog_post_service import (
    BlogPostService,
)

router = APIRouter(
    prefix="/blog-posts",
    tags=["Blog Posts"],
)


@router.post(
    "",
    response_model=BlogPostOut,
)
async def create_post(
    data: BlogPostCreate,
    db: AsyncSession = Depends(get_db),
):
    service = BlogPostService(db)
    return await service.create(data)


@router.get(
    "",
    response_model=list[BlogPostOut],
)
async def list_posts(
    db: AsyncSession = Depends(get_db),
):
    service = BlogPostService(db)
    return await service.list()


@router.get(
    "/published",
    response_model=list[BlogPostOut],
)
async def list_published_posts(
    db: AsyncSession = Depends(get_db),
):
    service = BlogPostService(db)
    return await service.list_published()


@router.get(
    "/{post_id}",
    response_model=BlogPostOut,
)
async def get_post(
    post_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    service = BlogPostService(db)

    post = await service.get(post_id)

    if post is None:
        raise HTTPException(
            status_code=404,
            detail="Post not found.",
        )

    return post


@router.put(
    "/{post_id}",
    response_model=BlogPostOut,
)
async def update_post(
    post_id: UUID,
    data: BlogPostUpdate,
    db: AsyncSession = Depends(get_db),
):
    service = BlogPostService(db)

    post = await service.get(post_id)

    if post is None:
        raise HTTPException(
            status_code=404,
            detail="Post not found.",
        )

    return await service.update(
        post,
        data,
    )


@router.patch(
    "/{post_id}/publish",
    response_model=BlogPostOut,
)
async def publish_post(
    post_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    service = BlogPostService(db)

    post = await service.get(post_id)

    if post is None:
        raise HTTPException(
            status_code=404,
            detail="Post not found.",
        )

    return await service.publish(post)


@router.patch(
    "/{post_id}/archive",
    response_model=BlogPostOut,
)
async def archive_post(
    post_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    service = BlogPostService(db)

    post = await service.get(post_id)

    if post is None:
        raise HTTPException(
            status_code=404,
            detail="Post not found.",
        )

    return await service.archive(post)


@router.delete(
    "/{post_id}",
    status_code=204,
)
async def delete_post(
    post_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    service = BlogPostService(db)

    post = await service.get(post_id)

    if post is None:
        raise HTTPException(
            status_code=404,
            detail="Post not found.",
        )

    await service.delete(post)