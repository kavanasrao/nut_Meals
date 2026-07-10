"""
Lot Traceability ORM model.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class LotTraceability(Base):
    __tablename__ = "lot_traceability"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    batch_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("production_batches.id"),
        nullable=False,
        index=True,
    )

    raw_material_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("raw_materials.id"),
        nullable=False,
        index=True,
    )

    supplier_lot_number: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    internal_lot_number: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
        unique=True,
    )

    expiry_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
