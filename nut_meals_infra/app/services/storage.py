"""
Object storage abstraction over boto3 (AWS S3 / OCI / MinIO).

All uploads are server-side encrypted (AES-256) AND client-side encrypted
with Fernet before upload — providing encryption-in-transit + at-rest.
"""

import asyncio
import hashlib
import io
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from typing import BinaryIO

import boto3
from boto3.s3.transfer import TransferConfig
from botocore.exceptions import ClientError

from app.core.config import settings
from app.core.logging import get_logger
from app.core.security import decrypt_bytes, encrypt_bytes

logger = get_logger(__name__)

_TRANSFER_CFG = TransferConfig(
    multipart_threshold=50 * 1024 * 1024,   # 50 MB
    multipart_chunksize=10 * 1024 * 1024,   # 10 MB
    max_concurrency=4,
    use_threads=True,
)


@lru_cache(maxsize=1)
def _get_s3_client():
    kwargs: dict = {
        "aws_access_key_id": settings.S3_ACCESS_KEY_ID,
        "aws_secret_access_key": settings.S3_SECRET_ACCESS_KEY,
        "region_name": settings.S3_REGION,
    }
    if settings.S3_ENDPOINT_URL:
        kwargs["endpoint_url"] = settings.S3_ENDPOINT_URL
    return boto3.client("s3", **kwargs)


def _build_s3_key(db_alias: str, job_id: str, timestamp: datetime) -> str:
    date_path = timestamp.strftime("%Y/%m/%d")
    ts = timestamp.strftime("%Y%m%dT%H%M%SZ")
    return f"{settings.S3_PATH_PREFIX}/{db_alias}/{date_path}/{db_alias}_{ts}_{job_id[:8]}.dump.enc"


async def upload_backup(
    data: bytes,
    db_alias: str,
    job_id: str,
    timestamp: datetime | None = None,
) -> tuple[str, str, str]:
    """
    Encrypt then upload backup bytes to object storage.

    Returns (s3_key, bucket, sha256_checksum).
    """
    ts = timestamp or datetime.now(timezone.utc)
    s3_key = _build_s3_key(db_alias, job_id, ts)

    # Client-side Fernet encryption
    encrypted = encrypt_bytes(data)
    checksum = hashlib.sha256(encrypted).hexdigest()

    s3 = _get_s3_client()

    def _upload():
        s3.upload_fileobj(
            io.BytesIO(encrypted),
            settings.S3_BUCKET_NAME,
            s3_key,
            Config=_TRANSFER_CFG,
            ExtraArgs={
                "ServerSideEncryption": "AES256",
                "Metadata": {
                    "db-alias": db_alias,
                    "job-id": job_id,
                    "sha256": checksum,
                    "encrypted": "fernet",
                },
                "StorageClass": "STANDARD_IA",
            },
        )

    await asyncio.get_event_loop().run_in_executor(None, _upload)
    logger.info("Backup uploaded", s3_key=s3_key, size_bytes=len(encrypted))
    return s3_key, settings.S3_BUCKET_NAME, checksum


async def download_backup(s3_key: str) -> bytes:
    """Download and decrypt a backup from object storage."""
    s3 = _get_s3_client()
    buf = io.BytesIO()

    def _download():
        s3.download_fileobj(settings.S3_BUCKET_NAME, s3_key, buf, Config=_TRANSFER_CFG)

    await asyncio.get_event_loop().run_in_executor(None, _download)
    encrypted = buf.getvalue()
    return decrypt_bytes(encrypted)


async def delete_backup(s3_key: str) -> None:
    s3 = _get_s3_client()
    await asyncio.get_event_loop().run_in_executor(
        None, lambda: s3.delete_object(Bucket=settings.S3_BUCKET_NAME, Key=s3_key)
    )
    logger.info("Backup deleted", s3_key=s3_key)


async def list_backups(db_alias: str | None = None) -> list[dict]:
    """List all backup objects, optionally filtered by db_alias."""
    s3 = _get_s3_client()
    prefix = f"{settings.S3_PATH_PREFIX}/{db_alias}/" if db_alias else f"{settings.S3_PATH_PREFIX}/"

    def _list():
        paginator = s3.get_paginator("list_objects_v2")
        objects = []
        for page in paginator.paginate(Bucket=settings.S3_BUCKET_NAME, Prefix=prefix):
            objects.extend(page.get("Contents", []))
        return objects

    objects = await asyncio.get_event_loop().run_in_executor(None, _list)
    return [{"key": o["Key"], "size": o["Size"], "last_modified": o["LastModified"]} for o in objects]


async def purge_expired_backups(retention_days: int | None = None) -> list[str]:
    """Delete backups older than retention_days. Returns list of deleted keys."""
    days = retention_days or settings.BACKUP_RETENTION_DAYS
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    objects = await list_backups()
    deleted = []
    for obj in objects:
        if obj["last_modified"] < cutoff:
            await delete_backup(obj["key"])
            deleted.append(obj["key"])
    logger.info("Purged expired backups", count=len(deleted), retention_days=days)
    return deleted


async def get_storage_stats() -> dict:
    objects = await list_backups()
    total_size = sum(o["size"] for o in objects)
    dates = [o["last_modified"] for o in objects]
    return {
        "bucket": settings.S3_BUCKET_NAME,
        "total_backups": len(objects),
        "total_size_bytes": total_size,
        "oldest_backup": min(dates) if dates else None,
        "newest_backup": max(dates) if dates else None,
    }


async def generate_presigned_url(s3_key: str, expiry_seconds: int = 3600) -> str:
    """Generate a time-limited pre-signed download URL."""
    s3 = _get_s3_client()
    url = await asyncio.get_event_loop().run_in_executor(
        None,
        lambda: s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.S3_BUCKET_NAME, "Key": s3_key},
            ExpiresIn=expiry_seconds,
        ),
    )
    return url
