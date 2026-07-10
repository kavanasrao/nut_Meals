"""Pydantic schemas for audit logs."""
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.audit import AuditSeverity


class AuditLogCreate(BaseModel):
    """Payload services submit to record a critical action.

    Typically services don't call the API synchronously in the hot path;
    instead they publish onto the `audit-events` Redis stream/Celery queue
    (see app/tasks/audit_tasks.py) and this schema is what gets deserialized
    on the consumer side. It's also exposed as a direct POST endpoint for
    low-volume / administrative use.
    """

    user_id: Optional[str] = None
    action: str = Field(..., max_length=128, description="e.g. 'order.created'")
    service: str = Field(..., max_length=64)
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    severity: AuditSeverity = AuditSeverity.INFO
    ip_address: Optional[str] = None
    metadata_json: Optional[dict] = None
    request_id: Optional[str] = None


class AuditLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: Optional[str]
    action: str
    service: str
    resource_type: Optional[str]
    resource_id: Optional[str]
    severity: AuditSeverity
    ip_address: Optional[str]
    metadata_json: Optional[dict]
    request_id: Optional[str]
    created_at: datetime


class AuditLogFilter(BaseModel):
    """Query params for listing/exporting audit logs."""

    user_id: Optional[str] = None
    action: Optional[str] = None
    service: Optional[str] = None
    resource_id: Optional[str] = None
    severity: Optional[AuditSeverity] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    limit: int = Field(100, ge=1, le=1000)
    offset: int = Field(0, ge=0)


class AuditExportRequest(BaseModel):
    filters: AuditLogFilter
    format: str = Field("csv", pattern="^(csv|json)$")


class AuditExportJobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    requested_by: str
    status: str
    result_path: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
