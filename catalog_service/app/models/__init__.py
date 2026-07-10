"""Aggregate all ORM models so Alembic's autogenerate can discover them via Base.metadata."""
from app.models.audit import AuditLog
from app.models.category import Category, Tag, product_tags
from app.models.product import Product, ProductAttribute, ProductStatus, ProductVariant
from app.models.redirect import Redirect, RedirectLog, RedirectType
from app.models.review import ProductRatingAggregate, Review, ReviewStatus
from app.models.seo import SEOMetadata

__all__ = [
    "AuditLog",
    "Category",
    "Tag",
    "product_tags",
    "Product",
    "ProductAttribute",
    "ProductStatus",
    "ProductVariant",
    "Redirect",
    "RedirectLog",
    "RedirectType",
    "ProductRatingAggregate",
    "Review",
    "ReviewStatus",
    "SEOMetadata",
]
