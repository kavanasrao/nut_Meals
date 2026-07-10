"""
Fire-and-forget event notification endpoint. Used by order/payment/
delivery services to trigger customer-facing alerts. Internally this
still goes through the Outbox pattern for reliability, but callers get
an immediate 202 without waiting on delivery.
"""
import hashlib
import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.rbac import require_notifier
from app.schemas.message import MessageCreate, MessageRead, NotificationTriggerRequest
from app.services.outbox_service import enqueue_message

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.post("/trigger", response_model=MessageRead, status_code=status.HTTP_202_ACCEPTED)
async def trigger_notification(
    request: NotificationTriggerRequest,
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_notifier),
):
    """
    Trigger an order status / payment confirmation / delivery update
    notification. Persisted via the outbox immediately; actual send
    happens asynchronously via Celery.
    """
    idem_key = request.idempotency_key or hashlib.sha256(
        f"{request.event_type}:{request.recipient}:{request.correlation_id}:{uuid.uuid4()}".encode()
    ).hexdigest()

    message = await enqueue_message(
        db,
        MessageCreate(
            event_type=request.event_type,
            channel=request.channel,
            recipient=request.recipient,
            subject=request.subject,
            body=request.body,
            payload=request.payload,
            correlation_id=request.correlation_id,
            priority=request.priority,
            idempotency_key=idem_key,
        ),
    )
    return message
