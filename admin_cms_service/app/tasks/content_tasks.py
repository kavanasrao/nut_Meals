"""
Celery tasks for the Content/Blog Manager: publishing scheduled posts
once their `publish_at` time arrives.
"""
import logging
from datetime import datetime, timezone

from sqlalchemy import select

from app.models.common import ContentStatus
from app.models.content import ContentItem
from app.tasks.celery_app import celery_app
from app.tasks.db import get_sync_db

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.content_tasks.publish_due_scheduled_content_task")
def publish_due_scheduled_content_task() -> list[str]:
    """
    Runs every minute (see celery_app.beat_schedule). Finds all
    SCHEDULED content items whose publish_at has passed and flips them
    to PUBLISHED.
    """
    now = datetime.now(timezone.utc)
    published_ids: list[str] = []

    with get_sync_db() as db:
        due_items = db.execute(
            select(ContentItem).where(
                ContentItem.status == ContentStatus.SCHEDULED,
                ContentItem.publish_at <= now,
            )
        ).scalars().all()

        for item in due_items:
            item.status = ContentStatus.PUBLISHED
            item.published_at = now
            published_ids.append(str(item.id))

    if published_ids:
        logger.info("Published %d scheduled content items: %s", len(published_ids), published_ids)

    return published_ids
