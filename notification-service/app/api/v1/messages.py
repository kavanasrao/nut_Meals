"""
Reliable multi-channel messaging API: create messages explicitly (rather
than the simplified /notifications/trigger), inspect status, and list
history with RBAC-gated access.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.rbac import require_notifier, require_read_access
from app.models.message import Message, MessageChannel, MessageStatus
from app.schemas.message import MessageCreate, MessageListResponse, MessageRead
from app.services.outbox_service import enqueue_message

router = APIRouter(prefix="/messages", tags=["messages"])


@router.post("", response_model=MessageRead, status_code=status.HTTP_202_ACCEPTED)
async def create_message(
    data: MessageCreate,
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_notifier),
):
    return await enqueue_message(db, data)


@router.get("/{message_id}", response_model=MessageRead)
async def get_message(
    message_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_read_access),
):
    result = await db.execute(select(Message).where(Message.id == message_id))
    message = result.scalar_one_or_none()
    if message is None:
        raise HTTPException(status_code=404, detail="Message not found")
    return message


@router.get("", response_model=MessageListResponse)
async def list_messages(
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_read_access),
    status_filter: MessageStatus | None = Query(default=None, alias="status"),
    channel: MessageChannel | None = None,
    correlation_id: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=200),
):
    query = select(Message)
    count_query = select(func.count()).select_from(Message)

    if status_filter:
        query = query.where(Message.status == status_filter)
        count_query = count_query.where(Message.status == status_filter)
    if channel:
        query = query.where(Message.channel == channel)
        count_query = count_query.where(Message.channel == channel)
    if correlation_id:
        query = query.where(Message.correlation_id == correlation_id)
        count_query = count_query.where(Message.correlation_id == correlation_id)

    total = (await db.execute(count_query)).scalar_one()
    query = query.order_by(Message.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    items = (await db.execute(query)).scalars().all()

    return MessageListResponse(items=items, total=total, page=page, page_size=page_size)
