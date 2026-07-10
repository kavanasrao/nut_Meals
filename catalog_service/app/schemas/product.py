"""Pydantic schemas for products, variants, attributes, categories, tags."""
import uuid
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.product import ProductStatus


# ---- Category ----
class CategoryBase(BaseModel):
    name: str = Field(..., max_length=150)
    slug: str = Field(..., max_length=180)
    description: Optional[str] = Field(None, max_length=1000)
    parent_id: Optional[uuid.UUID] = None
    is_active: bool = True


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=150)
    slug: Optional[str] = Field(None, max_length=180)
    description: Optional[str] = Field(None, max_length=1000)
    parent_id: Optional[uuid.UUID] = None
    is_active: Optional[bool] = None


class CategoryRead(CategoryBase):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID


# ---- Tag ----
class TagBase(BaseModel):
    name: str = Field(..., max_length=80)
    slug: str = Field(..., max_length=100)


class TagCreate(TagBase):
    pass


class TagRead(TagBase):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID


# ---- Attribute ----
class ProductAttributeBase(BaseModel):
    name: str = Field(..., max_length=100)
    value: str = Field(..., max_length=500)


class ProductAttributeCreate(ProductAttributeBase):
    pass


class ProductAttributeRead(ProductAttributeBase):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID


# ---- Variant ----
class ProductVariantBase(BaseModel):
    sku: str = Field(..., max_length=64)
    size: Optional[str] = Field(None, max_length=50)
    color: Optional[str] = Field(None, max_length=50)
    packaging: Optional[str] = Field(None, max_length=50)
    price_delta: Decimal = Decimal("0.00")
    extra: Optional[dict] = None


class ProductVariantCreate(ProductVariantBase):
    pass


class ProductVariantRead(ProductVariantBase):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    is_in_stock_cache: bool


class ProductVariantWithStock(ProductVariantRead):
    """Variant enriched with a live stock check from Inventory Service."""
    quantity_available: Optional[int] = None
    is_in_stock: bool


# ---- Product ----
class ProductBase(BaseModel):
    sku: str = Field(..., max_length=64)
    name: str = Field(..., max_length=255)
    slug: str = Field(..., max_length=280)
    description: Optional[str] = None
    base_price: Decimal = Field(..., ge=0)
    currency: str = Field(default="USD", max_length=3)
    status: ProductStatus = ProductStatus.DRAFT
    is_active: bool = True
    category_id: Optional[uuid.UUID] = None


class ProductCreate(ProductBase):
    tag_ids: List[uuid.UUID] = Field(default_factory=list)
    attributes: List[ProductAttributeCreate] = Field(default_factory=list)
    variants: List[ProductVariantCreate] = Field(default_factory=list)


class ProductUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    slug: Optional[str] = Field(None, max_length=280)
    description: Optional[str] = None
    base_price: Optional[Decimal] = Field(None, ge=0)
    currency: Optional[str] = Field(None, max_length=3)
    status: Optional[ProductStatus] = None
    is_active: Optional[bool] = None
    category_id: Optional[uuid.UUID] = None
    tag_ids: Optional[List[uuid.UUID]] = None


class ProductRead(ProductBase):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    tags: List[TagRead] = Field(default_factory=list)
    attributes: List[ProductAttributeRead] = Field(default_factory=list)
    variants: List[ProductVariantRead] = Field(default_factory=list)


class ProductDetail(ProductRead):
    """Full product detail including live inventory-enriched variants."""
    variants: List[ProductVariantWithStock] = Field(default_factory=list)
    average_rating: float = 0.0
    review_count: int = 0
