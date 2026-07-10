"""Core product catalog models: Product, ProductAttribute, ProductVariant."""
import uuid
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import ForeignKey, Numeric, String, Boolean, Text, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.database import Base
from app.models.category import product_tags
from app.models.mixins import TimestampMixin, UUIDPKMixin


class ProductStatus(str, enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


class Product(Base, UUIDPKMixin, TimestampMixin):
    """A sellable product. Variants (size/color/packaging) hang off this."""

    __tablename__ = "products"

    sku: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(280), unique=True, nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    base_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    status: Mapped[ProductStatus] = mapped_column(
        SAEnum(ProductStatus, name="product_status"), default=ProductStatus.DRAFT, nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    category_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("categories.id", ondelete="SET NULL"), nullable=True
    )

    category: Mapped[Optional["Category"]] = relationship(back_populates="products")
    tags: Mapped[List["Tag"]] = relationship(secondary=product_tags, back_populates="products")
    attributes: Mapped[List["ProductAttribute"]] = relationship(
        back_populates="product", cascade="all, delete-orphan"
    )
    variants: Mapped[List["ProductVariant"]] = relationship(
        back_populates="product", cascade="all, delete-orphan"
    )
    seo_metadata: Mapped[Optional["SEOMetadata"]] = relationship(
        back_populates="product", uselist=False, cascade="all, delete-orphan"
    )
    reviews: Mapped[List["Review"]] = relationship(
        back_populates="product", cascade="all, delete-orphan"
    )


class ProductAttribute(Base, UUIDPKMixin, TimestampMixin):
    """Arbitrary key/value product attribute (e.g. 'roast_level': 'medium')."""

    __tablename__ = "product_attributes"

    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    value: Mapped[str] = mapped_column(String(500), nullable=False)

    product: Mapped["Product"] = relationship(back_populates="attributes")


class ProductVariant(Base, UUIDPKMixin, TimestampMixin):
    """A purchasable variant of a product (size / color / packaging combo)."""

    __tablename__ = "product_variants"

    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    sku: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    size: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    color: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    packaging: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    price_delta: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    # Cached last-known stock status; source of truth is Inventory Service.
    # Refreshed synchronously on read (with short TTL cache) or async via webhook.
    is_in_stock_cache: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    extra: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    product: Mapped["Product"] = relationship(back_populates="variants")
