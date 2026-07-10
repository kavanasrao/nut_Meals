"""Production batch endpoints: create from BOM, track status, complete production."""
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, Roles, get_db, require_roles
from app.models.batch import BatchStatus
from app.schemas.batch import BatchCreate, BatchOut, BatchStatusUpdate
from app.services import batch_service
from app.tasks.batch_tasks import process_batch_completion_task

router = APIRouter(prefix="/batches", tags=["production-batches"])


@router.post("", response_model=BatchOut, status_code=201)
async def create_batch(
    payload: BatchCreate,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles(Roles.ADMIN, Roles.MANAGER)),
):
    """Create a production batch from a BOM after validating component availability."""
    return await batch_service.create_batch(db, payload, actor=user.subject)


@router.get("", response_model=list[BatchOut])
async def list_batches(
    status_filter: BatchStatus | None = None,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles(Roles.ADMIN, Roles.MANAGER, Roles.OPERATOR, Roles.VIEWER)),
):
    return await batch_service.list_batches(db, status_filter)


@router.get("/{batch_id}", response_model=BatchOut)
async def get_batch(
    batch_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles(Roles.ADMIN, Roles.MANAGER, Roles.OPERATOR, Roles.VIEWER)),
):
    return await batch_service.get_batch(db, batch_id)


@router.post("/{batch_id}/start", response_model=BatchOut)
async def start_batch(
    batch_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles(Roles.ADMIN, Roles.MANAGER, Roles.OPERATOR)),
):
    """Move batch to in-progress and consume BOM component stock."""
    return await batch_service.start_batch(db, batch_id, actor=user.subject)


@router.post("/{batch_id}/status", response_model=BatchOut)
async def update_batch_status(
    batch_id: uuid.UUID,
    payload: BatchStatusUpdate,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles(Roles.ADMIN, Roles.MANAGER, Roles.OPERATOR)),
):
    """Transition batch status. Completing a batch triggers an async task
    that finalizes inventory updates (idempotent; the sync path already
    applies changes but the task provides retry/backoff safety)."""
    if payload.status == BatchStatus.COMPLETED:
        if payload.actual_yield_quantity is None:
            from fastapi import HTTPException, status as http_status
            raise HTTPException(http_status.HTTP_400_BAD_REQUEST, "actual_yield_quantity is required to complete a batch")
        batch = await batch_service.complete_batch(db, batch_id, payload.actual_yield_quantity, actor=user.subject)
        process_batch_completion_task.delay(str(batch_id))
        return batch

    return await batch_service.cancel_or_fail_batch(db, batch_id, payload.status, actor=user.subject)
