"""Business logic for SEO metadata and schema.org structured data generation."""
import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product
from app.models.seo import SEOMetadata
from app.schemas.seo import SEOMetadataUpsert
from app.services.product_service import get_product, get_rating_aggregate


def build_structured_data(product: Product, seo: SEOMetadata) -> dict:
    """Build a schema.org/Product JSON-LD document for a product page."""
    data = {
        "@context": "https://schema.org/",
        "@type": "Product",
        "name": product.name,
        "sku": product.sku,
        "description": seo.meta_description or product.description,
        "offers": {
            "@type": "Offer",
            "priceCurrency": product.currency,
            "price": str(product.base_price),
            "availability": "https://schema.org/InStock"
            if product.is_active
            else "https://schema.org/OutOfStock",
        },
    }
    if seo.og_image_url:
        data["image"] = seo.og_image_url
    return data


async def upsert_seo_metadata(
    db: AsyncSession, product_id: uuid.UUID, payload: SEOMetadataUpsert
) -> SEOMetadata:
    product = await get_product(db, product_id)

    result = await db.execute(select(SEOMetadata).where(SEOMetadata.product_id == product_id))
    seo = result.scalar_one_or_none()
    if seo is None:
        seo = SEOMetadata(product_id=product_id, **payload.model_dump())
        db.add(seo)
    else:
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(seo, field, value)

    await db.flush()
    seo.structured_data = build_structured_data(product, seo)
    await db.flush()
    await db.refresh(seo)
    return seo


async def get_seo_metadata(db: AsyncSession, product_id: uuid.UUID) -> SEOMetadata:
    result = await db.execute(select(SEOMetadata).where(SEOMetadata.product_id == product_id))
    seo = result.scalar_one_or_none()
    if not seo:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="SEO metadata not found for product")
    return seo
