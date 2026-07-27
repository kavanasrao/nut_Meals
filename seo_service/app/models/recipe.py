"""
Recipe Content model.
"""

from __future__ import annotations

import enum
from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
    DateTime,
    Enum,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class RecipeStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    ARCHIVED = "ARCHIVED"


class DifficultyLevel(str, enum.Enum):
    EASY = "EASY"
    MEDIUM = "MEDIUM"
    HARD = "HARD"


class Recipe(Base):
    __tablename__ = "recipes"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    slug: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    ingredients: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    instructions: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    prep_time: Mapped[int] = mapped_column(
        nullable=False,
    )

    cook_time: Mapped[int] = mapped_column(
        nullable=False,
    )

    servings: Mapped[int] = mapped_column(
        nullable=False,
    )

    difficulty: Mapped[DifficultyLevel] = mapped_column(
        Enum(DifficultyLevel),
        nullable=False,
        default=DifficultyLevel.EASY,
    )

    calories: Mapped[float | None] = mapped_column(
        Numeric(8, 2),
        nullable=True,
    )

    protein: Mapped[float | None] = mapped_column(
        Numeric(8, 2),
        nullable=True,
    )

    carbohydrates: Mapped[float | None] = mapped_column(
        Numeric(8, 2),
        nullable=True,
    )

    fats: Mapped[float | None] = mapped_column(
        Numeric(8, 2),
        nullable=True,
    )

    featured_image: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    seo_title: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    seo_description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    seo_keywords: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    status: Mapped[RecipeStatus] = mapped_column(
        Enum(RecipeStatus),
        nullable=False,
        default=RecipeStatus.DRAFT,
    )

    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
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