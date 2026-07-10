"""
Backup service: coordinates pg_dump → encrypt → upload → record.

All heavy I/O (pg_dump subprocess, S3 upload) runs in a threadpool or
subprocess so the event loop is never blocked.
"""

import asyncio
import hashlib
import subprocess
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.models.backup import BackupJob, BackupStatus, BackupType
from app.services.storage import delete_backup, download_backup, upload_backup

logger = get_logger(__name__)

PGDUMP_TIMEOUT = 3600  # 1 hour hard cap


async def _run_pg_dump(dsn: str) -> bytes:
    """Run pg_dump asynchronously, return raw dump bytes."""
    cmd = [
        "pg_dump",
        "--no-password",
        "--format=custom",       # compressed, parallel-restorable
        "--compress=6",
        "--lock-wait-timeout=30s",
        dsn,
    ]
    logger.debug("Running pg_dump")
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env={"PGPASSWORD": ""},  # DSN carries the password; suppress prompt
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=PGDUMP_TIMEOUT)
    except asyncio.TimeoutError:
        proc.kill()
        raise RuntimeError("pg_dump timed out after 3600s")

    if proc.returncode != 0:
        raise RuntimeError(f"pg_dump failed (exit {proc.returncode}): {stderr.decode()[:500]}")

    logger.info("pg_dump completed", size_bytes=len(stdout))
    return stdout


async def create_backup_job(
    db: AsyncSession,
    db_alias: str,
    backup_type: BackupType = BackupType.FULL,
) -> BackupJob:
    """Create a new BackupJob record in PENDING state."""
    targets = settings.backup_db_targets_parsed()
    if db_alias not in targets:
        raise ValueError(f"Unknown DB alias '{db_alias}'. Known: {list(targets)}")

    expires = datetime.now(timezone.utc) + timedelta(days=settings.BACKUP_RETENTION_DAYS)
    job = BackupJob(
        id=uuid.uuid4(),
        db_alias=db_alias,
        backup_type=backup_type,
        status=BackupStatus.PENDING,
        encrypted=True,
        expires_at=expires,
    )
    db.add(job)
    await db.flush()
    return job


async def run_backup(db: AsyncSession, job: BackupJob) -> BackupJob:
    """
    Execute the full backup pipeline for a given job.
    Updates job record in-place and persists to DB.
    """
    targets = settings.backup_db_targets_parsed()
    dsn = targets[job.db_alias]

    job.status = BackupStatus.RUNNING
    job.started_at = datetime.now(timezone.utc)
    await db.flush()

    try:
        raw = await _run_pg_dump(dsn)
        ts = datetime.now(timezone.utc)
        s3_key, bucket, checksum = await upload_backup(
            data=raw,
            db_alias=job.db_alias,
            job_id=str(job.id),
            timestamp=ts,
        )
        job.status = BackupStatus.SUCCESS
        job.completed_at = datetime.now(timezone.utc)
        job.s3_key = s3_key
        job.s3_bucket = bucket
        job.size_bytes = len(raw)          # pre-encryption size for reference
        job.checksum_sha256 = checksum
    except Exception as exc:
        job.status = BackupStatus.FAILED
        job.error_message = str(exc)
        job.completed_at = datetime.now(timezone.utc)
        logger.error("Backup failed", db_alias=job.db_alias, job_id=str(job.id), error=str(exc))
        raise
    finally:
        await db.flush()

    logger.info(
        "Backup succeeded",
        db_alias=job.db_alias,
        job_id=str(job.id),
        s3_key=s3_key,
        size_bytes=job.size_bytes,
    )
    return job


async def restore_backup(
    job: BackupJob,
    target_dsn: str,
) -> None:
    """
    Download, decrypt, and restore a backup using pg_restore.
    target_dsn may differ from the original source.
    """
    logger.info("Starting restore", job_id=str(job.id), target_alias=job.db_alias)

    if not job.s3_key:
        raise ValueError("BackupJob has no S3 key — cannot restore")

    raw = await download_backup(job.s3_key)

    # Write to temp file (pg_restore requires seekable input for custom format)
    import tempfile, os

    with tempfile.NamedTemporaryFile(suffix=".dump", delete=False) as tmp:
        tmp.write(raw)
        tmp_path = tmp.name

    try:
        cmd = [
            "pg_restore",
            "--no-password",
            "--clean",
            "--if-exists",
            "--exit-on-error",
            f"--dbname={target_dsn}",
            tmp_path,
        ]
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=PGDUMP_TIMEOUT)
        if proc.returncode != 0:
            raise RuntimeError(f"pg_restore failed: {stderr.decode()[:500]}")
        logger.info("Restore completed", job_id=str(job.id))
    finally:
        os.unlink(tmp_path)


async def get_job(db: AsyncSession, job_id: uuid.UUID) -> BackupJob | None:
    result = await db.execute(select(BackupJob).where(BackupJob.id == job_id))
    return result.scalar_one_or_none()


async def list_jobs(
    db: AsyncSession,
    db_alias: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[BackupJob], int]:
    q = select(BackupJob)
    if db_alias:
        q = q.where(BackupJob.db_alias == db_alias)
    q = q.order_by(BackupJob.created_at.desc())

    from sqlalchemy import func, select as sel
    count_q = sel(func.count()).select_from(BackupJob)
    if db_alias:
        count_q = count_q.where(BackupJob.db_alias == db_alias)

    total = (await db.execute(count_q)).scalar_one()
    jobs = (await db.execute(q.limit(limit).offset(offset))).scalars().all()
    return list(jobs), total
