"""
Celery application + all task definitions.

Tasks use a dedicated asyncio loop per worker so async service code
can be called directly from sync Celery tasks.
"""

import asyncio
import uuid
from datetime import datetime, timezone

from celery import Celery
from celery.schedules import crontab
from celery.utils.log import get_task_logger

from app.core.config import settings

logger = get_task_logger(__name__)

celery_app = Celery(
    "nut_meals_infra",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    result_expires=86400,  # 24 h
    beat_schedule={
        "scheduled-backup-all-dbs": {
            "task": "app.services.celery_app.backup_all_databases",
            "schedule": crontab(**_parse_cron(settings.BACKUP_SCHEDULE_CRON)),
        },
        "purge-expired-backups": {
            "task": "app.services.celery_app.purge_expired_backups_task",
            "schedule": crontab(hour=3, minute=0),  # 03:00 UTC daily
        },
    },
)


def _run_async(coro):
    """Run an async coroutine from a sync Celery task."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def _parse_cron(cron_str: str) -> dict:
    """Parse '0 2 * * *' → kwargs for crontab()."""
    parts = cron_str.split()
    keys = ["minute", "hour", "day_of_month", "month_of_year", "day_of_week"]
    return {k: v for k, v in zip(keys, parts) if v != "*"}


# ─── Tasks ───────────────────────────────────────────────────────────────────

@celery_app.task(bind=True, name="app.services.celery_app.run_backup_task", max_retries=3)
def run_backup_task(self, db_alias: str, job_id: str):
    """Execute a single backup for *db_alias*, updating the BackupJob record."""
    from app.core.database import AsyncSessionLocal
    from app.models.backup import BackupStatus
    from app.services.backup_service import get_job, run_backup

    async def _execute():
        async with AsyncSessionLocal() as db:
            job = await get_job(db, uuid.UUID(job_id))
            if not job:
                logger.error("BackupJob not found", job_id=job_id)
                return
            job.celery_task_id = self.request.id
            try:
                await run_backup(db, job)
                await db.commit()
            except Exception as exc:
                await db.commit()
                raise self.retry(exc=exc, countdown=60 * (self.request.retries + 1))

    _run_async(_execute())
    return {"job_id": job_id, "status": "completed"}


@celery_app.task(name="app.services.celery_app.backup_all_databases")
def backup_all_databases():
    """Scheduled task: trigger a backup for every configured DB alias."""
    from app.core.database import AsyncSessionLocal
    from app.models.backup import BackupType
    from app.services.backup_service import create_backup_job

    targets = settings.backup_db_targets_parsed()
    dispatched = []

    async def _create_jobs():
        async with AsyncSessionLocal() as db:
            for alias in targets:
                job = await create_backup_job(db, alias, BackupType.FULL)
                await db.commit()
                dispatched.append(str(job.id))
                run_backup_task.delay(alias, str(job.id))
                logger.info("Backup dispatched", db_alias=alias, job_id=str(job.id))

    _run_async(_create_jobs())
    return {"dispatched": dispatched, "timestamp": datetime.now(timezone.utc).isoformat()}


@celery_app.task(name="app.services.celery_app.purge_expired_backups_task")
def purge_expired_backups_task():
    """Delete S3 objects and DB records past retention window."""
    from app.services.storage import purge_expired_backups

    deleted = _run_async(purge_expired_backups())
    logger.info("Purge complete", deleted_count=len(deleted))
    return {"deleted_keys": deleted}


@celery_app.task(bind=True, name="app.services.celery_app.restore_backup_task", max_retries=1)
def restore_backup_task(self, backup_job_id: str, target_db_alias: str):
    """Restore a backup into target_db_alias."""
    from app.core.database import AsyncSessionLocal
    from app.services.backup_service import get_job, restore_backup

    targets = settings.backup_db_targets_parsed()
    if target_db_alias not in targets:
        raise ValueError(f"Unknown target alias: {target_db_alias}")
    target_dsn = targets[target_db_alias]

    async def _restore():
        async with AsyncSessionLocal() as db:
            job = await get_job(db, uuid.UUID(backup_job_id))
            if not job:
                raise ValueError(f"BackupJob {backup_job_id} not found")
            await restore_backup(job, target_dsn)

    _run_async(_restore())
    return {"backup_job_id": backup_job_id, "target": target_db_alias, "status": "restored"}
