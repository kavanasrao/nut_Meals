"""
Celery tasks for keeping shipment tracking status current.

`sync_all_active_shipments` runs on a schedule (every 15 min, see
celery_app.beat_schedule) and fans out one `sync_single_shipment` task per
non-terminal shipment, so a slow/failing carrier call for one shipment never
blocks the rest of the batch.
"""
import asyncio
import logging

from app.core.celery_app import celery_app
from app.database import AsyncSessionLocal
from app.models.shipment import Shipment
from app.services.tracking import get_shipments_needing_sync, sync_shipment_tracking

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.tracking_sync.sync_all_active_shipments")
def sync_all_active_shipments() -> dict:
    """Entry point invoked by Celery beat: enumerates and fans out sync jobs."""
    return asyncio.run(_sync_all_active_shipments_async())


async def _sync_all_active_shipments_async() -> dict:
    async with AsyncSessionLocal() as db:
        shipments = await get_shipments_needing_sync(db)
        shipment_ids = [str(s.id) for s in shipments]

    for shipment_id in shipment_ids:
        sync_single_shipment.delay(shipment_id)

    logger.info("Queued tracking sync for %d shipments", len(shipment_ids))
    return {"queued": len(shipment_ids)}


@celery_app.task(
    name="app.tasks.tracking_sync.sync_single_shipment",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def sync_single_shipment(shipment_id: str) -> dict:
    """Sync tracking for a single shipment by id."""
    return asyncio.run(_sync_single_shipment_async(shipment_id))


async def _sync_single_shipment_async(shipment_id: str) -> dict:
    async with AsyncSessionLocal() as db:
        shipment = await db.get(Shipment, shipment_id)
        if shipment is None:
            logger.warning("Shipment %s not found during sync", shipment_id)
            return {"shipment_id": shipment_id, "status": "not_found"}

        await sync_shipment_tracking(db, shipment, actor="celery_tracking_sync")
        await db.commit()
        return {"shipment_id": shipment_id, "status": shipment.status.value}
