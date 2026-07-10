"""Dead Letter Queue inspection & reprocessing API (messaging_admin only for writes)."""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.rbac import require_messaging_admin, require_read_access
from app.models.dlq import DeadLetter
from app.schemas.dlq import DeadLetterRead, ReprocessRequest
from app.services.audit_service import record_audit_event

router = APIRouter(prefix="/dlq", tags=["dead-letter-queue"])


@router.get("", response_model=list[DeadLetterRead])
async def list_dead_letters(
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_read_access),
    channel: str | None = None,
    reprocessed: bool | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=200),
):
    query = select(DeadLetter)
    if channel:
        query = query.where(DeadLetter.channel == channel)
    if reprocessed is not None:
        query = query.where(DeadLetter.reprocessed == reprocessed)

    query = query.order_by(DeadLetter.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{dead_letter_id}", response_model=DeadLetterRead)
async def get_dead_letter(
    dead_letter_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_read_access),
):
    result = await db.execute(select(DeadLetter).where(DeadLetter.id == dead_letter_id))
    dl = result.scalar_one_or_none()
    if dl is None:
        raise HTTPException(status_code=404, detail="Dead letter not found")
    return dl


@router.post("/{dead_letter_id}/reprocess", status_code=status.HTTP_202_ACCEPTED)
async def reprocess_dead_letter(
    dead_letter_id: uuid.UUID,
    body: ReprocessRequest,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_messaging_admin),
):
    """Requeue a dead-lettered message for delivery. Enqueues a Celery task."""
    result = await db.execute(select(DeadLetter).where(DeadLetter.id == dead_letter_id))
    dl = result.scalar_one_or_none()
    if dl is None:
        raise HTTPException(status_code=404, detail="Dead letter not found")
    if dl.reprocessed:
        raise HTTPException(status_code=409, detail="Already reprocessed")

    from app.workers.tasks import process_dlq_task

    process_dlq_task.delay(str(dl.id), body.reset_attempts)

    from app.models.message import Message

    msg_result = await db.execute(select(Message).where(Message.id == dl.message_id))
    message = msg_result.scalar_one_or_none()
    if message:
        await record_audit_event(
            db, message, action="reprocess_requested", status="pending",
            detail={"note": body.note}, actor=user.sub,
        )

    return {"detail": "Reprocessing enqueued", "dead_letter_id": str(dead_letter_id)}
