import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class AuditLogRead(BaseModel):
    id: uuid.UUID
    message_id: uuid.UUID | None
    actor: str
    action: str
    channel: str | None
    recipient: str | None
    detail: dict[str, Any]
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class ComplianceReportRequest(BaseModel):
    start_date: datetime
    end_date: datetime
    channel: str | None = None
    status: str | None = None
    export_format: str = "csv"  # csv | json
