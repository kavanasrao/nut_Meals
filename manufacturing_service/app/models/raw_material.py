"""
SQLAlchemy ORM model for raw materials.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SAEnum,
    Numeric,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class RawMaterialStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    DISCONTINUED = "discontinued"


class UnitOfMeasure(str, enum.Enum):
    KG = "kg"
    G = "g"
    LITER = "liter"
    ML = "ml"
    PCS = "pcs"
    BOX = "box"
    PACK = "pack"


class RawMaterial(Base):
    __tablename__ = "raw_materials"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    code: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    description: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
    )

    category: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

    supplier_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )

    unit: Mapped[UnitOfMeasure] = mapped_column(
        SAEnum(UnitOfMeasure, name="unit_of_measure_enum"),
        nullable=False,
    )

    current_stock: Mapped[Decimal] = mapped_column(
        Numeric(12, 3),
        nullable=False,
        default=0,
    )

    reserved_stock: Mapped[Decimal] = mapped_column(
        Numeric(12, 3),
        nullable=False,
        default=0,
    )

    minimum_stock: Mapped[Decimal] = mapped_column(
        Numeric(12, 3),
        nullable=False,
        default=0,
    )

    reorder_level: Mapped[Decimal] = mapped_column(
        Numeric(12, 3),
        nullable=False,
        default=0,
    )

    reorder_quantity: Mapped[Decimal] = mapped_column(
        Numeric(12, 3),
        nullable=False,
        default=0,
    )

    unit_cost: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=0,
    )

    gst_rate: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        nullable=False,
        default=0,
    )

    warehouse_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )

    status: Mapped[RawMaterialStatus] = mapped_column(
        SAEnum(RawMaterialStatus, name="raw_material_status_enum"),
        nullable=False,
        default=RawMaterialStatus.ACTIVE,
        index=True,
    )

    is_perishable: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    shelf_life_days: Mapped[int | None] = mapped_column(
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )