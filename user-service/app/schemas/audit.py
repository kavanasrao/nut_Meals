"""Pydantic schemas for user audit logs."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel

from app.models.audit_log import AuditAction


class AuditLogOut(BaseModel):
    id: UUID
    user_id: Optional[UUID] = None
    action: AuditAction
    description: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    extra_data: Optional[dict[str, Any]] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class AuditLogListResponse(BaseModel):
    logs: list[AuditLogOut]
    total: int
    limit: int
    offset: int
