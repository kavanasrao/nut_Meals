"""Celery tasks for timed reservation release."""
import asyncio
import logging
import uuid

from celery import shared_task

from app.database import AsyncSessionLocal
from app.models.reservation import ReservationStatus
from app.services import reservation_service

logger = logging.getLogger("inventory.tasks.reservations")


def _run_async(coro):
    """Celery workers are sync; bridge into our async SQLAlchemy session."""
    return asyncio.run(coro)


async def _release_reservation(reservation_id: str) -> dict:
    async with AsyncSessionLocal() as db:
        reservation = await reservation_service.get_reservation(db, uuid.UUID(reservation_id))
        if reservation.status != ReservationStatus.ACTIVE:
            return {"reservation_id": reservation_id, "action": "skipped", "status": reservation.status.value}
        released = await reservation_service.release_reservation(
            db, uuid.UUID(reservation_id), actor="system:celery", reason="ttl_expired"
        )
        return {"reservation_id": reservation_id, "action": "released", "status": released.status.value}


async def _sweep_expired() -> int:
    async with AsyncSessionLocal() as db:
        return await reservation_service.release_expired_reservations(db)


@shared_task(name="app.tasks.reservation_tasks.release_reservation_task", bind=True, max_retries=3)
def release_reservation_task(self, reservation_id: str):
    """Scheduled at reservation-creation time with a countdown/eta matching
    the reservation TTL. If payment hasn't confirmed the reservation by
    then, this releases the held stock back to available inventory."""
    try:
        result = _run_async(_release_reservation(reservation_id))
        logger.info("reservation_release_task_completed", extra=result)
        return result
    except Exception as exc:
        logger.exception("reservation_release_task_failed", extra={"reservation_id": reservation_id})
        raise self.retry(exc=exc, countdown=15)


@shared_task(name="app.tasks.reservation_tasks.sweep_expired_reservations_task")
def sweep_expired_reservations_task():
    """Periodic safety-net sweep (see celery beat schedule) that catches any
    reservation whose per-item release task was lost or never scheduled."""
    count = _run_async(_sweep_expired())
    logger.info("reservation_sweep_completed", extra={"released_count": count})
    return {"released_count": count}
