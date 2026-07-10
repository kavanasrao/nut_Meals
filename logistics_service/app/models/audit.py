"""Audit log model for compliance and traceability of logistics actions."""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, JSON, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AuditLog(Base):
    """
    Immutable audit trail entry. Written for every state-changing action
    (shipment creation, status transition, carrier fallback, returns, etc.)
    to satisfy compliance/reporting requirements.
    """

    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)  # e.g. "shipment"
    entity_id: Mapped[str] = mapped_column(String(64), nullable=False)
    action: Mapped[str] = mapped_column(String(64), nullable=False)  # e.g. "carrier_fallback"
    actor: Mapped[str] = mapped_column(String(128), nullable=False)  # user id / "system"
    details: Mapped[dict] = mapped_column(JSON, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
