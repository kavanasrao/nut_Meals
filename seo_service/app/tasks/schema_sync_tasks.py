"""Celery tasks that (re)generate schema.org JSON-LD for entities."""
from __future__ import annotations

import asyncio
import logging

from celery import shared_task

from app.database import AsyncSessionLocal
from app.models.structured_data import SchemaType
from app.services.catalog_client import CatalogClient, UpstreamServiceError
from app.services.structured_data_service import (
    StructuredDataService,
    build_blog_posting_json_ld,
    build_product_json_ld,
    validate_product_json_ld,
)

logger = logging.getLogger(__name__)


async def _sync_product(product_id: str) -> None:
    catalog = CatalogClient()
    product = await catalog.get_product(product_id)
    try:
        reviews_summary = await catalog.get_product_reviews(product_id)
    except UpstreamServiceError:
        logger.warning("Reviews unavailable for product %s; continuing without ratings", product_id)
        reviews_summary = None

    json_ld = build_product_json_ld(product, reviews_summary)
    errors = validate_product_json_ld(json_ld)

    async with AsyncSessionLocal() as db:
        service = StructuredDataService(db)
        await service.upsert_record(
            entity_type="product",
            entity_id=product_id,
            schema_type=SchemaType.PRODUCT,
            json_ld=json_ld,
            validation_errors=errors or None,
        )
        await db.commit()


async def _sync_blog_post(post_id: str) -> None:
    catalog = CatalogClient()
    data = await catalog.list_blog_posts(page=1, page_size=1)
    post = next((p for p in data.get("items", []) if str(p["id"]) == post_id), None)
    if post is None:
        raise ValueError(f"Blog post {post_id} not found upstream")

    json_ld = build_blog_posting_json_ld(post)

    async with AsyncSessionLocal() as db:
        service = StructuredDataService(db)
        await service.upsert_record(
            entity_type="blog_post",
            entity_id=post_id,
            schema_type=SchemaType.BLOG_POSTING,
            json_ld=json_ld,
        )
        await db.commit()


@shared_task(name="app.tasks.schema_sync_tasks.sync_structured_data_task", bind=True, max_retries=3)
def sync_structured_data_task(self, entity_type: str, entity_id: str) -> str:
    """Regenerate and cache JSON-LD for a single entity after an upstream change."""
    try:
        if entity_type == "product":
            asyncio.run(_sync_product(entity_id))
        elif entity_type == "blog_post":
            asyncio.run(_sync_blog_post(entity_id))
        else:
            raise ValueError(f"Unsupported entity_type: {entity_type}")
        return "ok"
    except UpstreamServiceError as exc:
        raise self.retry(exc=exc, countdown=30) from exc
