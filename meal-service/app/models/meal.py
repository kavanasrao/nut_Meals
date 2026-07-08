"""Meal Service ORM models."""
from __future__ import annotations

import enum
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SAEnum,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class MealCategory(str, enum.Enum):
    BREAKFAST = "breakfast"
    LUNCH = "lunch"
    DINNER = "dinner"
    SNACKS = "snacks"
    BEVERAGES = "beverages"
    DESSERTS = "desserts"
    SPECIAL = "special"


class Meal(Base):
    __tablename__ = "meals"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )
    name: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    is_available: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    image_url: Mapped[str | None] = mapped_column(String(2048))

    # Nutritional info (optional, stored as JSON for flexibility)
    nutrition_info: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    # Searchable tags (e.g. ["vegan", "gluten-free"])
    tags: Mapped[list[str] | None] = mapped_column(ARRAY(String))

    # Inventory
    stock_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_daily_orders: Mapped[int | None] = mapped_column(Integer)

    # SEO / display
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_featured: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
