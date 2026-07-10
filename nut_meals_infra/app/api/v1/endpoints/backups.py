"""Backup management endpoints."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import verify_internal_api_key
from app.models.backup import BackupStatus, BackupType
from app.schemas.backup import BackupCreateRequest, BackupJobResponse, BackupListResponse
from app.services.backup_service import create_backup_job, get_job, list_jobs
from app.services.celery_app import run_backup_task
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(dependencies=[Depends(verify_internal_api_key)])


@router.post("/", response_model=BackupJobResponse, status_code=status.HTTP_202_ACCEPTED)
async def trigger_backup(
    req: BackupCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Trigger an on-demand backup for a given DB alias."""
    try:
        job = await create_backup_job(db, req.db_alias, req.backup_type)
        await db.commit()
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    # Enqueue Celery task
    task = run_backup_task.delay(req.db_alias, str(job.id))
    job.celery_task_id = task.id
    await db.commit()

    logger.info("Backup triggered", db_alias=req.db_alias, job_id=str(job.id), task_id=task.id)
    return BackupJobResponse.model_validate(job)


@router.get("/", response_model=BackupListResponse)
async def list_backup_jobs(
    db_alias: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    jobs, total = await list_jobs(db, db_alias=db_alias, limit=limit, offset=offset)
    return BackupListResponse(total=total, jobs=[BackupJobResponse.model_validate(j) for j in jobs])


@router.get("/{job_id}", response_model=BackupJobResponse)
async def get_backup_job(job_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    job = await get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Backup job not found")
    return BackupJobResponse.model_validate(job)


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_backup_job(job_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Mark a backup as deleted and remove its S3 object."""
    from app.services.storage import delete_backup

    job = await get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Backup job not found")
    if job.s3_key:
        await delete_backup(job.s3_key)
    job.status = BackupStatus.DELETED
    await db.commit()
