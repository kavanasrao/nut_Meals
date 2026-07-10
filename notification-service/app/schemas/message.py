import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models.message import MessageChannel, MessageStatus


class NotificationTriggerRequest(BaseModel):
    """Fire-and-forget event notification request (order/payment/delivery)."""
    event_type: str = Field(..., examples=["order.status_changed", "payment.confirmed", "delivery.updated"])
    recipient: str
    channel: MessageChannel
    subject: str | None = None
    body: str
    payload: dict[str, Any] = Field(default_factory=dict)
    correlation_id: str | None = None
    priority: int = Field(default=5, ge=1, le=9)
    idempotency_key: str | None = None


class MessageCreate(BaseModel):
    event_type: str
    channel: MessageChannel
    recipient: str
    subject: str | None = None
    body: str
    payload: dict[str, Any] = Field(default_factory=dict)
    correlation_id: str | None = None
    priority: int = Field(default=5, ge=1, le=9)
    idempotency_key: str
    max_retries: int = 5


class MessageRead(BaseModel):
    id: uuid.UUID
    event_type: str
    channel: MessageChannel
    recipient: str
    subject: str | None
    status: MessageStatus
    attempt_count: int
    max_retries: int
    next_retry_at: datetime | None
    last_error: str | None
    correlation_id: str | None
    priority: int
    created_at: datetime
    updated_at: datetime
    sent_at: datetime | None

    class Config:
        from_attributes = True


class MessageListResponse(BaseModel):
    items: list[MessageRead]
    total: int
    page: int
    page_size: int
