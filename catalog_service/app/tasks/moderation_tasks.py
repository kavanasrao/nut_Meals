"""Background tasks triggered by the review moderation workflow."""
import logging
import uuid

from app.database import AsyncSessionLocal
from app.tasks.celery_app import celery_app
from app.tasks.db_utils import run_async

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.moderation_tasks.recompute_rating_aggregate_task", bind=True, max_retries=3)
def recompute_rating_aggregate_task(self, product_id: str) -> None:
    """Asynchronously recompute a product's aggregate rating.

    This mirrors the synchronous recompute done inline in review_service, and
    exists so that batch moderation actions or external moderation events
    (e.g. a webhook from a third-party moderation tool) stay eventually
    consistent without blocking the request path.
    """
    from app.services.review_service import recompute_rating_aggregate

    async def _run():
        async with AsyncSessionLocal() as db:
            await recompute_rating_aggregate(db, uuid.UUID(product_id))
            await db.commit()

    try:
        run_async(_run)
        logger.info("rating_aggregate_recomputed", extra={"product_id": product_id})
    except Exception as exc:  # noqa: BLE001
        logger.exception("rating_aggregate_recompute_failed", extra={"product_id": product_id})
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)


@celery_app.task(name="app.tasks.moderation_tasks.auto_flag_review_task")
def auto_flag_review_task(review_id: str, reason: str) -> None:
    """Placeholder hook for automated content-moderation (e.g. profanity /
    spam classifier) to flag a review for priority human review.

    Kept as a lightweight, explicit task boundary so a real classifier
    integration can be dropped in without touching the API layer.
    """
    logger.info("review_auto_flagged", extra={"review_id": review_id, "reason": reason})
