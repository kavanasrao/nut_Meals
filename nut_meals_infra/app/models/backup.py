"""ORM models for tracking backup jobs and their metadata."""

import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import UUID, BigInteger, DateTime, Enum, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class BackupStatus(str, PyEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    DELETED = "deleted"


class BackupType(str, PyEnum):
    FULL = "full"
    INCREMENTAL = "incremental"


class BackupJob(Base):
    __tablename__ = "backup_jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    db_alias: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    backup_type: Mapped[BackupType] = mapped_column(Enum(BackupType), default=BackupType.FULL)
    status: Mapped[BackupStatus] = mapped_column(
        Enum(BackupStatus), default=BackupStatus.PENDING, index=True
    )

    # Storage location
    s3_key: Mapped[str | None] = mapped_column(String(512))
    s3_bucket: Mapped[str | None] = mapped_column(String(128))
    size_bytes: Mapped[int | None] = mapped_column(BigInteger)

    # Metadata
    checksum_sha256: Mapped[str | None] = mapped_column(String(64))
    encrypted: Mapped[bool] = mapped_column(default=True)
    error_message: Mapped[str | None] = mapped_column(Text)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)

    # Celery task reference
    celery_task_id: Mapped[str | None] = mapped_column(String(128))

    def __repr__(self) -> str:
        return f"<BackupJob id={self.id} db={self.db_alias} status={self.status}>"
