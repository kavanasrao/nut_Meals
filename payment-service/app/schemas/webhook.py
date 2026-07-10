"""
Webhook schemas.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel

from app.models.webhook import WebhookStatus


class WebhookOut(BaseModel):
    id: UUID
    provider: str
    event_id: str
    event_type: str
    verified: bool
    status: WebhookStatus
    payload: dict[str, Any]
    received_at: datetime
    processed_at: datetime | None

    model_config = {
        "from_attributes": True
    }