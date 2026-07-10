"""
SQLAlchemy ORM model for BOM Items.
"""

from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import (
    ForeignKey,
    Numeric,
    String,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

class BOMItem(Base):
    __tablename__ = "bom_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    bom_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("boms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    raw_material_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("raw_materials.id"),
        nullable=False,
        index=True,
    )

    quantity: Mapped[Decimal] = mapped_column(
        Numeric(12, 3),
        nullable=False,
    )

    wastage_percent: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        nullable=False,
        default=0,
    )

    remarks: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )