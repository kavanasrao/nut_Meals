"""SEO metadata endpoints, consumed by the storefront frontend for rendering
<title>, <meta>, Open Graph tags, and JSON-LD structured data."""
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rbac import CurrentUser, Role, require_roles
from app.database import get_db
from app.schemas.seo import SEOMetadataRead, SEOMetadataUpsert
from app.services import seo_service

router = APIRouter(prefix="/api/v1/products/{product_id}/seo", tags=["seo"])


@router.get("", response_model=SEOMetadataRead)
async def get_seo_metadata(product_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Public endpoint the frontend calls at render time to populate SEO tags."""
    return await seo_service.get_seo_metadata(db, product_id)


@router.put("", response_model=SEOMetadataRead)
async def upsert_seo_metadata(
    product_id: uuid.UUID,
    payload: SEOMetadataUpsert,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles(Role.CATALOG_ADMIN)),
):
    """Create or update SEO metadata for a product, regenerating structured data."""
    seo = await seo_service.upsert_seo_metadata(db, product_id, payload)
    await db.commit()
    return seo
