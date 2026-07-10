"""
Builds schema.org JSON-LD structured data compliant with Google Rich
Results requirements, and caches it in `StructuredDataRecord`.

Reference requirements enforced here (kept in sync with Google's
structured data guidelines):
  - Product: name, image, offers.price/priceCurrency/availability required
  - Review/AggregateRating: reviewRating, author required
  - BlogPosting: headline, image, author, datePublished required
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.structured_data import SchemaType, StructuredDataRecord

settings = get_settings()


def build_product_json_ld(product: dict[str, Any], reviews_summary: dict[str, Any] | None) -> dict:
    json_ld: dict[str, Any] = {
        "@context": "https://schema.org/",
        "@type": "Product",
        "name": product["name"],
        "sku": product.get("sku"),
        "image": product.get("images", []),
        "description": product.get("description", ""),
        "brand": {"@type": "Brand", "name": product.get("brand", "nut_Meals")},
        "offers": {
            "@type": "Offer",
            "url": f"{settings.PUBLIC_BASE_URL}/products/{product['slug']}",
            "priceCurrency": product.get("currency", "USD"),
            "price": str(product["price"]),
            "availability": (
                "https://schema.org/InStock"
                if product.get("in_stock", True)
                else "https://schema.org/OutOfStock"
            ),
        },
    }
    if reviews_summary and reviews_summary.get("review_count", 0) > 0:
        json_ld["aggregateRating"] = {
            "@type": "AggregateRating",
            "ratingValue": str(reviews_summary["average_rating"]),
            "reviewCount": str(reviews_summary["review_count"]),
        }
    return json_ld


def build_blog_posting_json_ld(post: dict[str, Any]) -> dict:
    return {
        "@context": "https://schema.org/",
        "@type": "BlogPosting",
        "headline": post["title"],
        "image": post.get("cover_image", ""),
        "author": {"@type": "Person", "name": post.get("author_name", "nut_Meals Team")},
        "datePublished": post["published_at"],
        "dateModified": post.get("updated_at", post["published_at"]),
        "mainEntityOfPage": {
            "@type": "WebPage",
            "@id": f"{settings.PUBLIC_BASE_URL}/blog/{post['slug']}",
        },
    }


def validate_product_json_ld(json_ld: dict) -> list[str]:
    """Minimal Google Rich Results required-field validation for Product."""
    errors = []
    for field in ("name", "image", "offers"):
        if not json_ld.get(field):
            errors.append(f"Missing required field: {field}")
    offers = json_ld.get("offers", {})
    for field in ("price", "priceCurrency", "availability"):
        if not offers.get(field):
            errors.append(f"Missing required offers.{field}")
    return errors


class StructuredDataService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def upsert_record(
        self,
        *,
        entity_type: str,
        entity_id: str,
        schema_type: SchemaType,
        json_ld: dict,
        validation_errors: list[str] | None = None,
    ) -> StructuredDataRecord:
        result = await self.db.execute(
            select(StructuredDataRecord).where(
                StructuredDataRecord.entity_type == entity_type,
                StructuredDataRecord.entity_id == entity_id,
                StructuredDataRecord.schema_type == schema_type,
            )
        )
        record = result.scalar_one_or_none()
        is_valid = not validation_errors
        errors_payload = {"errors": validation_errors} if validation_errors else None

        if record is None:
            record = StructuredDataRecord(
                entity_type=entity_type,
                entity_id=entity_id,
                schema_type=schema_type,
                json_ld=json_ld,
                is_valid=is_valid,
                validation_errors=errors_payload,
            )
            self.db.add(record)
        else:
            record.json_ld = json_ld
            record.is_valid = is_valid
            record.validation_errors = errors_payload
            record.generated_at = datetime.now(timezone.utc)
        await self.db.flush()
        return record

    async def get_record(
        self, entity_type: str, entity_id: str, schema_type: SchemaType
    ) -> StructuredDataRecord | None:
        result = await self.db.execute(
            select(StructuredDataRecord).where(
                StructuredDataRecord.entity_type == entity_type,
                StructuredDataRecord.entity_id == entity_id,
                StructuredDataRecord.schema_type == schema_type,
            )
        )
        return result.scalar_one_or_none()
