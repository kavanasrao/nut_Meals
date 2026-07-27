"""
API routes for Blog Categories.
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
from app.schemas.blog_category import (
    BlogCategoryCreate,
    BlogCategoryOut,
    BlogCategoryUpdate,
)
from app.services.blog_category_service import (
    BlogCategoryService,
)

router = APIRouter(
    prefix="/blog-categories",
    tags=["Blog Categories"],
)


@router.post(
    "",
    response_model=BlogCategoryOut,
)
async def create_category(
    data: BlogCategoryCreate,
    db: AsyncSession = Depends(get_db),
):
    service = BlogCategoryService(db)
    return await service.create(data)


@router.get(
    "",
    response_model=list[BlogCategoryOut],
)
async def list_categories(
    db: AsyncSession = Depends(get_db),
):
    service = BlogCategoryService(db)
    return await service.list()


@router.get(
    "/{category_id}",
    response_model=BlogCategoryOut,
)
async def get_category(
    category_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    service = BlogCategoryService(db)

    category = await service.get(category_id)

    if category is None:
        raise HTTPException(
            status_code=404,
            detail="Category not found.",
        )

    return category


@router.put(
    "/{category_id}",
    response_model=BlogCategoryOut,
)
async def update_category(
    category_id: UUID,
    data: BlogCategoryUpdate,
    db: AsyncSession = Depends(get_db),
):
    service = BlogCategoryService(db)

    category = await service.get(category_id)

    if category is None:
        raise HTTPException(
            status_code=404,
            detail="Category not found.",
        )

    return await service.update(
        category,
        data,
    )


@router.delete(
    "/{category_id}",
    status_code=204,
)
async def delete_category(
    category_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    service = BlogCategoryService(db)

    category = await service.get(category_id)

    if category is None:
        raise HTTPException(
            status_code=404,
            detail="Category not found.",
        )

    await service.delete(category)