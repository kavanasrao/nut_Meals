"""Business logic for product catalog management."""
import uuid
from typing import Optional, Sequence

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.product import Product, ProductAttribute, ProductVariant
from app.models.category import Tag
from app.models.review import ProductRatingAggregate
from app.schemas.product import ProductCreate, ProductUpdate
from app.services.inventory_client import InventoryClient


async def _get_tags(db: AsyncSession, tag_ids: Sequence[uuid.UUID]) -> list[Tag]:
    if not tag_ids:
        return []
    result = await db.execute(select(Tag).where(Tag.id.in_(tag_ids)))
    tags = list(result.scalars().all())
    if len(tags) != len(set(tag_ids)):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="One or more tag_ids not found")
    return tags


async def create_product(db: AsyncSession, payload: ProductCreate) -> Product:
    existing = await db.execute(select(Product).where(Product.sku == payload.sku))
    if existing.scalar_one_or_none():
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Product SKU already exists")

    tags = await _get_tags(db, payload.tag_ids)

    product = Product(
        sku=payload.sku,
        name=payload.name,
        slug=payload.slug,
        description=payload.description,
        base_price=payload.base_price,
        currency=payload.currency,
        status=payload.status,
        is_active=payload.is_active,
        category_id=payload.category_id,
        tags=tags,
        attributes=[ProductAttribute(**a.model_dump()) for a in payload.attributes],
        variants=[ProductVariant(**v.model_dump()) for v in payload.variants],
    )
    db.add(product)
    await db.flush()
    await db.refresh(product, attribute_names=["tags", "attributes", "variants"])
    return product


async def get_product(db: AsyncSession, product_id: uuid.UUID) -> Product:
    result = await db.execute(
        select(Product)
        .options(
            selectinload(Product.tags),
            selectinload(Product.attributes),
            selectinload(Product.variants),
            selectinload(Product.category),
        )
        .where(Product.id == product_id)
    )
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Product not found")
    return product


async def get_product_by_slug(db: AsyncSession, slug: str) -> Product:
    result = await db.execute(
        select(Product)
        .options(
            selectinload(Product.tags),
            selectinload(Product.attributes),
            selectinload(Product.variants),
        )
        .where(Product.slug == slug)
    )
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Product not found")
    return product


async def list_products(
    db: AsyncSession,
    *,
    page: int = 1,
    page_size: int = 20,
    category_id: Optional[uuid.UUID] = None,
    status_filter: Optional[str] = None,
    search: Optional[str] = None,
) -> tuple[list[Product], int]:
    query = select(Product).options(
        selectinload(Product.tags), selectinload(Product.attributes), selectinload(Product.variants)
    )
    count_query = select(func.count()).select_from(Product)

    if category_id:
        query = query.where(Product.category_id == category_id)
        count_query = count_query.where(Product.category_id == category_id)
    if status_filter:
        query = query.where(Product.status == status_filter)
        count_query = count_query.where(Product.status == status_filter)
    if search:
        like = f"%{search}%"
        query = query.where(Product.name.ilike(like))
        count_query = count_query.where(Product.name.ilike(like))

    total = (await db.execute(count_query)).scalar_one()
    query = query.offset((page - 1) * page_size).limit(page_size).order_by(Product.created_at.desc())
    items = (await db.execute(query)).scalars().unique().all()
    return list(items), total


async def update_product(db: AsyncSession, product_id: uuid.UUID, payload: ProductUpdate) -> Product:
    product = await get_product(db, product_id)
    data = payload.model_dump(exclude_unset=True, exclude={"tag_ids"})
    for field, value in data.items():
        setattr(product, field, value)

    if payload.tag_ids is not None:
        product.tags = await _get_tags(db, payload.tag_ids)

    await db.flush()
    await db.refresh(product, attribute_names=["tags", "attributes", "variants"])
    return product


async def delete_product(db: AsyncSession, product_id: uuid.UUID) -> None:
    product = await get_product(db, product_id)
    await db.delete(product)
    await db.flush()


async def enrich_with_stock(product: Product, client: InventoryClient) -> list[dict]:
    """Combine cached stock flags with a live Inventory Service lookup."""
    skus = [v.sku for v in product.variants]
    stock_map = await client.get_stock_for_skus(skus)
    enriched = []
    for v in product.variants:
        live = stock_map.get(v.sku)
        enriched.append(
            {
                "id": v.id,
                "sku": v.sku,
                "size": v.size,
                "color": v.color,
                "packaging": v.packaging,
                "price_delta": v.price_delta,
                "extra": v.extra,
                "is_in_stock_cache": v.is_in_stock_cache,
                "is_in_stock": live["is_in_stock"] if live else v.is_in_stock_cache,
                "quantity_available": live.get("quantity_available") if live else None,
            }
        )
    return enriched


async def get_rating_aggregate(db: AsyncSession, product_id: uuid.UUID) -> ProductRatingAggregate:
    result = await db.execute(
        select(ProductRatingAggregate).where(ProductRatingAggregate.product_id == product_id)
    )
    agg = result.scalar_one_or_none()
    if not agg:
        return ProductRatingAggregate(product_id=product_id, average_rating=0.0, review_count=0)
    return agg
