"""Business logic for categories and tags."""
import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.category import Category, Tag
from app.schemas.product import CategoryCreate, CategoryUpdate, TagCreate


async def create_category(db: AsyncSession, payload: CategoryCreate) -> Category:
    existing = await db.execute(select(Category).where(Category.slug == payload.slug))
    if existing.scalar_one_or_none():
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Category slug already exists")
    category = Category(**payload.model_dump())
    db.add(category)
    await db.flush()
    await db.refresh(category)
    return category


async def get_category(db: AsyncSession, category_id: uuid.UUID) -> Category:
    result = await db.execute(select(Category).where(Category.id == category_id))
    category = result.scalar_one_or_none()
    if not category:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Category not found")
    return category


async def list_categories(db: AsyncSession) -> list[Category]:
    result = await db.execute(select(Category).where(Category.is_active.is_(True)))
    return list(result.scalars().all())


async def update_category(db: AsyncSession, category_id: uuid.UUID, payload: CategoryUpdate) -> Category:
    category = await get_category(db, category_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(category, field, value)
    await db.flush()
    await db.refresh(category)
    return category


async def delete_category(db: AsyncSession, category_id: uuid.UUID) -> None:
    category = await get_category(db, category_id)
    await db.delete(category)
    await db.flush()


async def create_tag(db: AsyncSession, payload: TagCreate) -> Tag:
    existing = await db.execute(select(Tag).where(Tag.slug == payload.slug))
    if existing.scalar_one_or_none():
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Tag slug already exists")
    tag = Tag(**payload.model_dump())
    db.add(tag)
    await db.flush()
    await db.refresh(tag)
    return tag


async def list_tags(db: AsyncSession) -> list[Tag]:
    result = await db.execute(select(Tag))
    return list(result.scalars().all())
