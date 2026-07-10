"""Pydantic v2 schemas for backup and recovery endpoints."""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.backup import BackupStatus, BackupType


class BackupCreateRequest(BaseModel):
    db_alias: str = Field(..., description="Target DB alias defined in BACKUP_DB_TARGETS")
    backup_type: BackupType = BackupType.FULL


class BackupJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    db_alias: str
    backup_type: BackupType
    status: BackupStatus
    s3_key: Optional[str] = None
    s3_bucket: Optional[str] = None
    size_bytes: Optional[int] = None
    checksum_sha256: Optional[str] = None
    encrypted: bool
    error_message: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    celery_task_id: Optional[str] = None


class BackupListResponse(BaseModel):
    total: int
    jobs: list[BackupJobResponse]


class RestoreRequest(BaseModel):
    backup_job_id: uuid.UUID
    target_db_alias: str = Field(..., description="DB alias to restore into (can differ from source)")
    confirm: bool = Field(False, description="Must be true — restore is destructive")


class RestoreJobResponse(BaseModel):
    task_id: str
    backup_job_id: uuid.UUID
    target_db_alias: str
    status: str = "queued"
    message: str


class StorageStatsResponse(BaseModel):
    bucket: str
    total_backups: int
    total_size_bytes: int
    oldest_backup: Optional[datetime] = None
    newest_backup: Optional[datetime] = None
