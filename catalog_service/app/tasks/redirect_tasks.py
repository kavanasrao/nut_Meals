"""Background tasks for the redirect manager: analytics sync + housekeeping."""
import logging
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, func, select

from app.database import AsyncSessionLocal
from app.models.redirect import Redirect, RedirectLog
from app.tasks.celery_app import celery_app
from app.tasks.db_utils import run_async

logger = logging.getLogger(__name__)

STALE_LOG_RETENTION_DAYS = 180


@celery_app.task(name="app.tasks.redirect_tasks.sync_redirect_analytics_task", bind=True, max_retries=3)
def sync_redirect_analytics_task(self, redirect_id: str) -> None:
    """Fire-and-forget task per redirect hit; extend here to push events to an
    external analytics pipeline (e.g. Kafka topic, BigQuery, Segment)."""

    async def _run():
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(func.count()).select_from(RedirectLog).where(
                    RedirectLog.redirect_id == uuid.UUID(redirect_id)
                )
            )
            hit_count = result.scalar_one()
            logger.info("redirect_hit_recorded", extra={"redirect_id": redirect_id, "total_hits": hit_count})

    try:
        run_async(_run)
    except Exception as exc:  # noqa: BLE001
        logger.exception("redirect_analytics_sync_failed", extra={"redirect_id": redirect_id})
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)


@celery_app.task(name="app.tasks.redirect_tasks.flush_redirect_analytics")
def flush_redirect_analytics() -> None:
    """Periodic (hourly) task: aggregate redirect hit counts for reporting.
    Scheduled via celery beat; see tasks/celery_app.py."""

    async def _run():
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Redirect.source_path, func.count(RedirectLog.id))
                .join(RedirectLog, RedirectLog.redirect_id == Redirect.id)
                .group_by(Redirect.source_path)
            )
            rows = result.all()
            logger.info("redirect_analytics_flushed", extra={"redirect_count": len(rows)})

    run_async(_run)


@celery_app.task(name="app.tasks.redirect_tasks.cleanup_old_redirect_logs")
def cleanup_old_redirect_logs() -> None:
    """Periodic (daily) task: purge redirect usage logs older than the
    retention window to keep the table lean."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=STALE_LOG_RETENTION_DAYS)

    async def _run():
        async with AsyncSessionLocal() as db:
            result = await db.execute(delete(RedirectLog).where(RedirectLog.resolved_at < cutoff))
            await db.commit()
            logger.info("stale_redirect_logs_purged", extra={"deleted": result.rowcount})

    run_async(_run)
