"""Unit tests for app.services.content_service, focused on scheduling logic."""
import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app.models.common import ContentStatus, ContentType
from app.schemas.content import ContentItemCreate
from app.services import content_service


@pytest.mark.asyncio
async def test_get_due_scheduled_items_returns_only_past_due(db_session):
    author_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    due_item = await content_service.create_content_item(
        db_session,
        data=ContentItemCreate(
            content_type=ContentType.BLOG_POST,
            title="Due Post",
            slug="due-post",
            body="Body",
            publish_at=now - timedelta(minutes=5),
        ),
        author_admin_id=author_id,
    )

    future_item = await content_service.create_content_item(
        db_session,
        data=ContentItemCreate(
            content_type=ContentType.BLOG_POST,
            title="Future Post",
            slug="future-post-2",
            body="Body",
            publish_at=now + timedelta(hours=1),
        ),
        author_admin_id=author_id,
    )

    due_items = await content_service.get_due_scheduled_items(db_session, as_of=now)
    due_ids = {item.id for item in due_items}

    assert due_item.id in due_ids
    assert future_item.id not in due_ids


@pytest.mark.asyncio
async def test_create_without_publish_at_is_draft(db_session):
    author_id = uuid.uuid4()
    item = await content_service.create_content_item(
        db_session,
        data=ContentItemCreate(
            content_type=ContentType.FAQ,
            title="Immediate FAQ",
            slug="immediate-faq",
            body="Body",
        ),
        author_admin_id=author_id,
    )
    assert item.status == ContentStatus.DRAFT


@pytest.mark.asyncio
async def test_archive_content_item_sets_status(db_session):
    author_id = uuid.uuid4()
    item = await content_service.create_content_item(
        db_session,
        data=ContentItemCreate(
            content_type=ContentType.ANNOUNCEMENT,
            title="Old Announcement",
            slug="old-announcement",
            body="Body",
        ),
        author_admin_id=author_id,
    )
    archived = await content_service.archive_content_item(db_session, content_id=item.id)
    assert archived.status == ContentStatus.ARCHIVED
