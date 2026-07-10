"""Product, category, and tag CRUD endpoints."""
import uuid

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import write_audit_log
from app.core.rbac import CurrentUser, Role, require_roles
from app.database import get_db
from app.schemas.common import Page
from app.schemas.product import (
    CategoryCreate,
    CategoryRead,
    CategoryUpdate,
    ProductCreate,
    ProductDetail,
    ProductRead,
    ProductUpdate,
    ProductVariantWithStock,
    TagCreate,
    TagRead,
)
from app.services import category_service, product_service
from app.services.inventory_client import InventoryClient, get_inventory_client

router = APIRouter(prefix="/api/v1", tags=["catalog"])


# ---------------- Products ----------------
@router.post("/products", response_model=ProductRead, status_code=201)
async def create_product(
    payload: ProductCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles(Role.CATALOG_ADMIN)),
):
    """Create a new product with optional attributes/variants/tags."""
    product = await product_service.create_product(db, payload)
    await write_audit_log(
        db,
        actor_id=user.id,
        actor_role=user.role.value,
        action="product.create",
        resource_type="product",
        resource_id=str(product.id),
        ip_address=request.client.host if request.client else None,
    )
    await db.commit()
    return product


@router.get("/products", response_model=Page[ProductRead])
async def list_products(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    category_id: uuid.UUID | None = None,
    status: str | None = None,
    search: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """List products with pagination and optional filters. Public read."""
    items, total = await product_service.list_products(
        db, page=page, page_size=page_size, category_id=category_id, status_filter=status, search=search
    )
    return Page(items=items, total=total, page=page, page_size=page_size)


@router.get("/products/{product_id}", response_model=ProductDetail)
async def get_product(
    product_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    inventory: InventoryClient = Depends(get_inventory_client),
):
    """Fetch full product detail, including live inventory-enriched variants
    and aggregate rating. Public read."""
    product = await product_service.get_product(db, product_id)
    enriched_variants = await product_service.enrich_with_stock(product, inventory)
    aggregate = await product_service.get_rating_aggregate(db, product_id)

    detail = ProductDetail.model_validate(product)
    detail.variants = [ProductVariantWithStock(**v) for v in enriched_variants]
    detail.average_rating = aggregate.average_rating
    detail.review_count = aggregate.review_count
    return detail


@router.get("/products/slug/{slug}", response_model=ProductRead)
async def get_product_by_slug(slug: str, db: AsyncSession = Depends(get_db)):
    """Resolve a product by its SEO-friendly slug (used by storefront frontend)."""
    return await product_service.get_product_by_slug(db, slug)


@router.patch("/products/{product_id}", response_model=ProductRead)
async def update_product(
    product_id: uuid.UUID,
    payload: ProductUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles(Role.CATALOG_ADMIN)),
):
    product = await product_service.update_product(db, product_id, payload)
    await write_audit_log(
        db,
        actor_id=user.id,
        actor_role=user.role.value,
        action="product.update",
        resource_type="product",
        resource_id=str(product_id),
        detail=payload.model_dump(exclude_unset=True, mode="json"),
        ip_address=request.client.host if request.client else None,
    )
    await db.commit()
    return product


@router.delete("/products/{product_id}", status_code=204)
async def delete_product(
    product_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles(Role.CATALOG_ADMIN)),
):
    await product_service.delete_product(db, product_id)
    await write_audit_log(
        db,
        actor_id=user.id,
        actor_role=user.role.value,
        action="product.delete",
        resource_type="product",
        resource_id=str(product_id),
        ip_address=request.client.host if request.client else None,
    )
    await db.commit()


# ---------------- Categories ----------------
@router.post("/categories", response_model=CategoryRead, status_code=201)
async def create_category(
    payload: CategoryCreate,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles(Role.CATALOG_ADMIN)),
):
    category = await category_service.create_category(db, payload)
    await db.commit()
    return category


@router.get("/categories", response_model=list[CategoryRead])
async def list_categories(db: AsyncSession = Depends(get_db)):
    return await category_service.list_categories(db)


@router.patch("/categories/{category_id}", response_model=CategoryRead)
async def update_category(
    category_id: uuid.UUID,
    payload: CategoryUpdate,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles(Role.CATALOG_ADMIN)),
):
    category = await category_service.update_category(db, category_id, payload)
    await db.commit()
    return category


@router.delete("/categories/{category_id}", status_code=204)
async def delete_category(
    category_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles(Role.CATALOG_ADMIN)),
):
    await category_service.delete_category(db, category_id)
    await db.commit()


# ---------------- Tags ----------------
@router.post("/tags", response_model=TagRead, status_code=201)
async def create_tag(
    payload: TagCreate,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles(Role.CATALOG_ADMIN)),
):
    tag = await category_service.create_tag(db, payload)
    await db.commit()
    return tag


@router.get("/tags", response_model=list[TagRead])
async def list_tags(db: AsyncSession = Depends(get_db)):
    return await category_service.list_tags(db)
