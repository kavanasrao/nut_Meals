"""Pydantic schemas for compliance reporting."""
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.compliance import ComplianceFramework, ReportStatus


class ComplianceReportDefinitionCreate(BaseModel):
    name: str = Field(..., max_length=128)
    framework: ComplianceFramework
    description: Optional[str] = None
    check_config_json: Optional[dict] = None


class ComplianceReportDefinitionOut(ComplianceReportDefinitionCreate):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime


class ComplianceReportRunRequest(BaseModel):
    definition_id: uuid.UUID


class ComplianceFinding(BaseModel):
    """A single pass/fail check within a report, with supporting evidence."""

    check_id: str
    description: str
    passed: bool
    evidence: Optional[dict] = None
    remediation: Optional[str] = None


class ComplianceReportRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    definition_id: uuid.UUID
    framework: ComplianceFramework
    status: ReportStatus
    requested_by: str
    readiness_score: Optional[float] = None
    findings_json: Optional[dict] = None
    export_path: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
