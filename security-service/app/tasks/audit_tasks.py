"""
Celery tasks for background audit-log processing.

Ingestion pipeline:
  other-service --(publish)--> Redis list "audit:pending" --(this worker)-->
  batched INSERT into audit_logs, via ingest_audit_event() / flush_audit_batch().

Two entry points are provided intentionally:
  - `ingest_audit_event`: called per-event (e.g. from a service's own Celery
    producer) for lower-volume services or when immediate persistence matters.
  - `flush_audit_batch`: a periodic task (see celery_app.beat_schedule) that
    drains a Redis buffer in batches for very high-volume producers (e.g.
    the Orders/Payments services under load), trading a few seconds of
    latency for much lower DB write amplification.
"""
import asyncio
import json
import logging
import uuid

import redis
from celery import shared_task

from app.config import get_settings
from app.database import AsyncSessionLocal
from app.schemas.audit import AuditLogCreate
from app.services.audit_service import AuditService

logger = logging.getLogger("security-service.tasks")
settings = get_settings()

_PENDING_KEY = "audit:pending"
_BATCH_SIZE = 500


def _redis_client() -> redis.Redis:
    return redis.from_url(settings.REDIS_URL, decode_responses=True)


def _run_async(coro):
    """Run an async coroutine from within a synchronous Celery task."""
    return asyncio.run(coro)


@shared_task(name="app.tasks.audit_tasks.ingest_audit_event", bind=True, max_retries=3, default_retry_delay=5)
def ingest_audit_event(self, event_payload: dict) -> str:
    """Persist a single audit event immediately.

    `event_payload` is the JSON-serializable dict form of AuditLogCreate,
    typically produced by another service like:

        celery_app.send_task(
            "app.tasks.audit_tasks.ingest_audit_event",
            args=[{"action": "order.created", "service": "orders", "user_id": "...", ...}],
            queue="audit_events",
        )
    """
    try:
        payload = AuditLogCreate(**event_payload)

        async def _do():
            async with AsyncSessionLocal() as db:
                service = AuditService(db)
                log = await service.create_log(payload)
                return str(log.id)

        return _run_async(_do())
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to ingest audit event, retrying: %s", exc)
        raise self.retry(exc=exc)


@shared_task(name="app.tasks.audit_tasks.buffer_audit_event")
def buffer_audit_event(event_payload: dict) -> None:
    """Lightweight producer-side helper: push an event onto the Redis buffer
    for later batched flushing, instead of hitting Postgres per-event.
    Preferred path for very high-throughput services."""
    client = _redis_client()
    client.rpush(_PENDING_KEY, json.dumps(event_payload))


@shared_task(name="app.tasks.audit_tasks.flush_audit_batch")
def flush_audit_batch() -> int:
    """Drain up to _BATCH_SIZE buffered events from Redis and bulk-insert them.
    Runs on a schedule (see celery_app.beat_schedule) so audit writes are
    eventually-consistent within ~10s even under heavy producer load."""
    client = _redis_client()
    pipe = client.pipeline()
    pipe.lrange(_PENDING_KEY, 0, _BATCH_SIZE - 1)
    pipe.ltrim(_PENDING_KEY, _BATCH_SIZE, -1)
    raw_events, _ = pipe.execute()

    if not raw_events:
        return 0

    payloads = []
    for raw in raw_events:
        try:
            payloads.append(AuditLogCreate(**json.loads(raw)))
        except Exception:  # noqa: BLE001
            logger.warning("Dropping malformed audit event: %s", raw)

    if not payloads:
        return 0

    async def _do():
        async with AsyncSessionLocal() as db:
            service = AuditService(db)
            return await service.bulk_create(payloads)

    count = _run_async(_do())
    logger.info("Flushed %d buffered audit events", count)
    return count


@shared_task(name="app.tasks.audit_tasks.run_audit_export", bind=True, max_retries=2, default_retry_delay=10)
def run_audit_export(self, job_id: str) -> str:
    """Execute a previously-created AuditExportJob (see POST /audit/logs/export)."""
    try:
        async def _do():
            async with AsyncSessionLocal() as db:
                service = AuditService(db)
                await service.run_export(uuid.UUID(job_id))

        _run_async(_do())
        return job_id
    except Exception as exc:  # noqa: BLE001
        logger.exception("Audit export job %s failed, retrying: %s", job_id, exc)
        raise self.retry(exc=exc)


@shared_task(name="app.tasks.audit_tasks.cleanup_stale_export_jobs")
def cleanup_stale_export_jobs() -> int:
    """Nightly housekeeping: mark export jobs stuck in 'running' for >24h as failed,
    so they don't appear as silently hung in the compliance dashboard."""
    from datetime import datetime, timedelta

    from sqlalchemy import select

    from app.models.audit import AuditExportJob

    async def _do():
        cutoff = datetime.utcnow() - timedelta(hours=24)
        async with AsyncSessionLocal() as db:
            stmt = select(AuditExportJob).where(
                AuditExportJob.status == "running", AuditExportJob.created_at < cutoff
            )
            result = await db.execute(stmt)
            stale_jobs = result.scalars().all()
            for job in stale_jobs:
                job.status = "failed"
                job.error_message = "Export exceeded 24h processing window; marked stale by cleanup task."
            await db.commit()
            return len(stale_jobs)

    count = _run_async(_do())
    logger.info("Marked %d stale export jobs as failed", count)
    return count
