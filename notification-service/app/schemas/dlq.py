import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class DeadLetterRead(BaseModel):
    id: uuid.UUID
    message_id: uuid.UUID
    channel: str
    recipient: str
    payload_snapshot: dict[str, Any]
    failure_reason: str
    attempt_count: int
    reprocessed: bool
    reprocessed_at: datetime | None
    created_at: datetime

    class Config:
        from_attributes = True


class ReprocessRequest(BaseModel):
    reset_attempts: bool = True
    note: str | None = None
