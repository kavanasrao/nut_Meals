"""Business logic for the Content/Blog Manager."""
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.common import ContentStatus, ContentType
from app.models.content import ContentItem, ContentRevision
from app.schemas.content import ContentItemCreate, ContentItemUpdate


async def create_content_item(
    db: AsyncSession, *, data: ContentItemCreate, author_admin_id: uuid.UUID
) -> ContentItem:
    existing = await db.execute(select(ContentItem).where(ContentItem.slug == data.slug))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=f"Slug '{data.slug}' already exists")

    status_value = ContentStatus.SCHEDULED if data.publish_at else ContentStatus.DRAFT

    item = ContentItem(
        content_type=data.content_type,
        title=data.title,
        slug=data.slug,
        body=data.body,
        excerpt=data.excerpt,
        tags=data.tags,
        seo_title=data.seo_title,
        seo_description=data.seo_description,
        seo_keywords=data.seo_keywords,
        og_image_url=data.og_image_url,
        canonical_url=data.canonical_url,
        publish_at=data.publish_at,
        status=status_value,
        author_admin_id=author_admin_id,
    )
    db.add(item)
    await db.flush()
    await db.refresh(item)
    return item


async def get_content_item(db: AsyncSession, content_id: uuid.UUID) -> ContentItem:
    item = await db.get(ContentItem, content_id)
    if item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Content item not found")
    return item


async def list_content_items(
    db: AsyncSession,
    *,
    content_type: Optional[ContentType] = None,
    status_filter: Optional[ContentStatus] = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[ContentItem], int]:
    query = select(ContentItem)
    count_query = select(func.count()).select_from(ContentItem)

    if content_type is not None:
        query = query.where(ContentItem.content_type == content_type)
        count_query = count_query.where(ContentItem.content_type == content_type)
    if status_filter is not None:
        query = query.where(ContentItem.status == status_filter)
        count_query = count_query.where(ContentItem.status == status_filter)

    total = (await db.execute(count_query)).scalar_one()

    query = query.order_by(ContentItem.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    items = (await db.execute(query)).scalars().all()
    return list(items), total


async def update_content_item(
    db: AsyncSession, *, content_id: uuid.UUID, data: ContentItemUpdate, editor_admin_id: uuid.UUID
) -> ContentItem:
    item = await get_content_item(db, content_id)

    # Snapshot the pre-edit state as a revision before mutating.
    revision = ContentRevision(
        content_item_id=item.id,
        title=item.title,
        body=item.body,
        edited_by_admin_id=editor_admin_id,
    )
    db.add(revision)

    update_fields = data.model_dump(exclude_unset=True)
    for field, value in update_fields.items():
        setattr(item, field, value)

    await db.flush()
    await db.refresh(item)
    return item


async def publish_content_item(db: AsyncSession, *, content_id: uuid.UUID) -> ContentItem:
    """Immediately publish a content item, bypassing schedule."""
    item = await get_content_item(db, content_id)
    item.status = ContentStatus.PUBLISHED
    item.published_at = datetime.now(timezone.utc)
    await db.flush()
    await db.refresh(item)
    return item


async def archive_content_item(db: AsyncSession, *, content_id: uuid.UUID) -> ContentItem:
    item = await get_content_item(db, content_id)
    item.status = ContentStatus.ARCHIVED
    await db.flush()
    await db.refresh(item)
    return item


async def delete_content_item(db: AsyncSession, *, content_id: uuid.UUID) -> None:
    item = await get_content_item(db, content_id)
    await db.delete(item)
    await db.flush()


async def get_due_scheduled_items(db: AsyncSession, *, as_of: datetime) -> list[ContentItem]:
    """Used by the Celery beat task to find scheduled posts ready to publish."""
    query = select(ContentItem).where(
        ContentItem.status == ContentStatus.SCHEDULED,
        ContentItem.publish_at <= as_of,
    )
    return list((await db.execute(query)).scalars().all())
