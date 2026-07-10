"""Category and Tag models for product taxonomy."""
import uuid
from typing import List, Optional

from sqlalchemy import ForeignKey, String, Table, Column
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.mixins import TimestampMixin, UUIDPKMixin

# Many-to-many association: products <-> tags
product_tags = Table(
    "product_tags",
    Base.metadata,
    Column("product_id", UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", UUID(as_uuid=True), ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)


class Category(Base, UUIDPKMixin, TimestampMixin):
    """Hierarchical product category (self-referential tree)."""

    __tablename__ = "categories"

    name: Mapped[str] = mapped_column(String(150), nullable=False)
    slug: Mapped[str] = mapped_column(String(180), unique=True, nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    parent_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("categories.id", ondelete="SET NULL"), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    children: Mapped[List["Category"]] = relationship(
        "Category", backref="parent", remote_side="Category.id"
    )
    products: Mapped[List["Product"]] = relationship(back_populates="category")


class Tag(Base, UUIDPKMixin, TimestampMixin):
    """Free-form product tag (e.g. 'vegan', 'gluten-free', 'best-seller')."""

    __tablename__ = "tags"

    name: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)

    products: Mapped[List["Product"]] = relationship(
        secondary=product_tags, back_populates="tags"
    )
