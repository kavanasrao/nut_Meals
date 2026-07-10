"""
Compliance models.

Compliance "reports" are named, versioned definitions (e.g. "PCI DSS Quarterly
Access Review", "GDPR Data Processing Readiness") that map to a set of checks
run against audit logs, RBAC bindings, and WAF incidents. Each execution is
recorded as a ComplianceReportRun so results are reproducible and auditable
in their own right.
"""
import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ComplianceFramework(str, enum.Enum):
    PCI_DSS = "pci_dss"
    GDPR = "gdpr"
    SOC2 = "soc2"


class ReportStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ComplianceReportDefinition(Base):
    """A reusable, named definition of a compliance report."""

    __tablename__ = "compliance_report_definitions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    framework: Mapped[ComplianceFramework] = mapped_column(Enum(ComplianceFramework), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    check_config_json: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True, doc="Parameters for the checks this report runs, e.g. lookback window"
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class ComplianceReportRun(Base):
    """A single execution of a ComplianceReportDefinition, with computed results."""

    __tablename__ = "compliance_report_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    definition_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    framework: Mapped[ComplianceFramework] = mapped_column(Enum(ComplianceFramework), nullable=False, index=True)
    status: Mapped[ReportStatus] = mapped_column(Enum(ReportStatus), default=ReportStatus.PENDING, index=True)
    requested_by: Mapped[str] = mapped_column(String(128), nullable=False)
    readiness_score: Mapped[float | None] = mapped_column(
        Float, nullable=True, doc="0-100 composite score, computed from passed/failed checks"
    )
    findings_json: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True, doc="Structured list of checks with pass/fail + evidence references"
    )
    export_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, index=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
