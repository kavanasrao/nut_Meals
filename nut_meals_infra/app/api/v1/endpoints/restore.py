"""Restore endpoint — deliberately requires explicit confirmation flag."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import verify_internal_api_key
from app.models.backup import BackupStatus
from app.schemas.backup import RestoreJobResponse, RestoreRequest
from app.services.backup_service import get_job
from app.services.celery_app import restore_backup_task
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(dependencies=[Depends(verify_internal_api_key)])


@router.post("/", response_model=RestoreJobResponse, status_code=status.HTTP_202_ACCEPTED)
async def trigger_restore(
    req: RestoreRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Restore a backup into a target database.

    ⚠️  DESTRUCTIVE — wipes the target DB before restoring.
    Requires `confirm: true` in the request body.
    """
    if not req.confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Set confirm=true to acknowledge this is a destructive operation.",
        )

    job = await get_job(db, req.backup_job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Backup job not found")
    if job.status != BackupStatus.SUCCESS:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot restore a backup in '{job.status}' state — only 'success' allowed.",
        )

    task = restore_backup_task.delay(str(job.id), req.target_db_alias)
    logger.info(
        "Restore triggered",
        backup_job_id=str(job.id),
        target=req.target_db_alias,
        task_id=task.id,
    )
    return RestoreJobResponse(
        task_id=task.id,
        backup_job_id=job.id,
        target_db_alias=req.target_db_alias,
        message="Restore job queued. Monitor task status via Celery.",
    )
