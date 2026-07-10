"""
Celery tasks that rebuild sitemap entries/files and generate bulk AI
exports. Each task opens its own short-lived async DB session (Celery
workers are sync by default, so we bridge with `asyncio.run`).
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from celery import shared_task

from app.database import AsyncSessionLocal
from app.models.sitemap import ChangeFrequency, SitemapEntityType
from app.services.ai_discovery_service import AiDiscoveryService, build_product_embedding_metadata
from app.services.catalog_client import CatalogClient, UpstreamServiceError
from app.services.sitemap_service import SitemapService

logger = logging.getLogger(__name__)


async def _resync_products() -> int:
    catalog = CatalogClient()
    count = 0
    async with AsyncSessionLocal() as db:
        service = SitemapService(db)
        page = 1
        while True:
            data = await catalog.list_products(page=page, page_size=500)
            products = data.get("items", [])
            if not products:
                break
            for product in products:
                await service.upsert_entry(
                    entity_type=SitemapEntityType.PRODUCT,
                    entity_id=str(product["id"]),
                    loc=product["canonical_url"],
                    lastmod=datetime.fromisoformat(product["updated_at"]),
                    changefreq=ChangeFrequency.DAILY,
                    priority=0.8 if product.get("in_stock", True) else 0.3,
                    is_active=product.get("is_published", True),
                )
                count += 1
            await service.generate_files_for_type(SitemapEntityType.PRODUCT)
            await db.commit()
            if not data.get("has_next"):
                break
            page += 1
    return count


async def _resync_categories() -> int:
    catalog = CatalogClient()
    count = 0
    async with AsyncSessionLocal() as db:
        service = SitemapService(db)
        page = 1
        while True:
            data = await catalog.list_categories(page=page, page_size=500)
            categories = data.get("items", [])
            if not categories:
                break
            for category in categories:
                await service.upsert_entry(
                    entity_type=SitemapEntityType.CATEGORY,
                    entity_id=str(category["id"]),
                    loc=category["canonical_url"],
                    lastmod=datetime.fromisoformat(category["updated_at"]),
                    changefreq=ChangeFrequency.WEEKLY,
                    priority=0.6,
                )
                count += 1
            await service.generate_files_for_type(SitemapEntityType.CATEGORY)
            await db.commit()
            if not data.get("has_next"):
                break
            page += 1
    return count


async def _resync_blog_posts() -> int:
    catalog = CatalogClient()
    count = 0
    async with AsyncSessionLocal() as db:
        service = SitemapService(db)
        page = 1
        while True:
            data = await catalog.list_blog_posts(page=page, page_size=500)
            posts = data.get("items", [])
            if not posts:
                break
            for post in posts:
                await service.upsert_entry(
                    entity_type=SitemapEntityType.BLOG_POST,
                    entity_id=str(post["id"]),
                    loc=post["canonical_url"],
                    lastmod=datetime.fromisoformat(post["updated_at"]),
                    changefreq=ChangeFrequency.MONTHLY,
                    priority=0.5,
                )
                count += 1
            await service.generate_files_for_type(SitemapEntityType.BLOG_POST)
            await db.commit()
            if not data.get("has_next"):
                break
            page += 1
    return count


async def _rebuild(entity_type: str | None) -> dict:
    results = {}
    try:
        if entity_type in (None, SitemapEntityType.PRODUCT.value):
            results["products"] = await _resync_products()
        if entity_type in (None, SitemapEntityType.CATEGORY.value):
            results["categories"] = await _resync_categories()
        if entity_type in (None, SitemapEntityType.BLOG_POST.value):
            results["blog_posts"] = await _resync_blog_posts()
    except UpstreamServiceError:
        logger.exception("Sitemap rebuild failed due to upstream error")
        raise

    async with AsyncSessionLocal() as db:
        service = SitemapService(db)
        await service.regenerate_index()
        await db.commit()
    return results


@shared_task(name="app.tasks.sitemap_tasks.rebuild_sitemap_task", bind=True, max_retries=3)
def rebuild_sitemap_task(self, entity_type: str | None, force: bool = False) -> dict:
    """Resync sitemap entries from upstream services and regenerate XML files."""
    try:
        return asyncio.run(_rebuild(entity_type))
    except UpstreamServiceError as exc:
        raise self.retry(exc=exc, countdown=30) from exc


async def _generate_ai_export(batch_id: str) -> None:
    catalog = CatalogClient()
    async with AsyncSessionLocal() as db:
        service = AiDiscoveryService(db)
        await service.mark_running(batch_id)
        await db.commit()

    records = []
    try:
        page = 1
        while True:
            data = await catalog.list_products(page=page, page_size=500)
            products = data.get("items", [])
            if not products:
                break
            records.extend(build_product_embedding_metadata(p) for p in products)
            if not data.get("has_next"):
                break
            page += 1
    except UpstreamServiceError:
        async with AsyncSessionLocal() as db:
            service = AiDiscoveryService(db)
            await service.mark_failed(batch_id, "Catalog service unavailable during export")
            await db.commit()
        raise

    ndjson_bytes = AiDiscoveryService.to_ndjson(records)
    file_path = f"/data/ai-exports/{batch_id}.ndjson"
    with open(file_path, "wb") as fh:
        fh.write(ndjson_bytes)

    async with AsyncSessionLocal() as db:
        service = AiDiscoveryService(db)
        await service.mark_complete(
            batch_id, file_path=file_path, record_count=len(records), ndjson_bytes=ndjson_bytes
        )
        await db.commit()


@shared_task(name="app.tasks.sitemap_tasks.generate_ai_export_task", bind=True, max_retries=2)
def generate_ai_export_task(self, batch_id: str | None) -> str | None:
    """Generate a bulk NDJSON catalog export for AI ingestion pipelines."""
    if batch_id is None:
        # Scheduled (beat) invocation with no explicit batch — create one.
        async def _create_and_run() -> str:
            async with AsyncSessionLocal() as db:
                service = AiDiscoveryService(db)
                batch = await service.create_batch(requested_by="scheduler")
                await db.commit()
                new_id = str(batch.id)
            await _generate_ai_export(new_id)
            return new_id

        return asyncio.run(_create_and_run())

    try:
        asyncio.run(_generate_ai_export(batch_id))
        return batch_id
    except UpstreamServiceError as exc:
        raise self.retry(exc=exc, countdown=60) from exc
