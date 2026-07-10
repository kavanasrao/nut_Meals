"""Celery tasks supporting batch production.

Inventory updates for batch start/completion are applied synchronously in
the API request path (app/services/batch_service.py) so the caller gets an
immediate, consistent response. These tasks provide asynchronous
downstream work that should not block that response: notifying dependent
services (e.g. Orders/Catalog) that new finished-product stock exists, and
retrying that notification with backoff if it fails.
"""
import asyncio
import logging
import uuid

import httpx
from celery import shared_task

from app.config import get_settings
from app.database import AsyncSessionLocal
from app.services.batch_service import get_batch
from app.services.bom_service import get_bom

logger = logging.getLogger("inventory.tasks.batches")
settings = get_settings()


def _run_async(coro):
    return asyncio.run(coro)


async def _notify_downstream_of_batch_completion(batch_id: str) -> dict:
    async with AsyncSessionLocal() as db:
        batch = await get_batch(db, uuid.UUID(batch_id))
        bom = await get_bom(db, batch.bom_id)

    payload = {
        "batch_id": str(batch.id),
        "product_item_id": str(bom.product_item_id),
        "warehouse_id": str(batch.warehouse_id),
        "quantity_added": float(batch.actual_yield_quantity or 0),
        "lot_number": batch.lot_number,
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"{settings.ORDERS_SERVICE_BASE_URL}/internal/stock-events/production-completed",
                json=payload,
            )
            resp.raise_for_status()
    except httpx.HTTPError as exc:
        logger.warning("downstream_notify_failed", extra={"batch_id": batch_id, "error": str(exc)})
        raise
    return payload


@shared_task(
    name="app.tasks.batch_tasks.process_batch_completion_task",
    bind=True,
    max_retries=5,
    default_retry_delay=20,
)
def process_batch_completion_task(self, batch_id: str):
    """Notify downstream services (e.g. Orders, Catalog availability caches)
    that a batch completed and finished-product stock increased."""
    try:
        result = _run_async(_notify_downstream_of_batch_completion(batch_id))
        logger.info("batch_completion_notified", extra=result)
        return result
    except Exception as exc:
        raise self.retry(exc=exc)
