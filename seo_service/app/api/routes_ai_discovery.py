"""
AI discovery readiness endpoints: per-product embedding metadata for
real-time RAG lookups, and bulk NDJSON export batches for offline
ingestion by AI search/embedding pipelines (ours or third-party,
gated by the same RBAC/robots rules as the rest of the site).
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.api.deps import Catalog, DbSession
from app.core.security import CurrentUser, Role, require_roles
from app.services.ai_discovery_service import AiDiscoveryService, build_product_embedding_metadata
from app.services.catalog_client import UpstreamServiceError
from app.tasks.sitemap_tasks import generate_ai_export_task

router = APIRouter(prefix="/ai-discovery", tags=["ai-discovery"])


@router.get("/products/{product_id}/metadata")
async def get_product_ai_metadata(product_id: str, catalog: Catalog) -> dict:
    """Real-time embedding-friendly metadata for a single product, used by
    our own RAG/search-assist features and well-behaved AI crawlers."""
    try:
        product = await catalog.get_product(product_id)
    except UpstreamServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail="Catalog service unavailable"
        ) from exc
    return build_product_embedding_metadata(product)


@router.post("/export", status_code=status.HTTP_202_ACCEPTED)
async def request_ai_export(
    db: DbSession,
    user: Annotated[CurrentUser, Depends(require_roles(Role.SEO_EDITOR, Role.ADMIN))],
) -> dict:
    """Kick off a bulk NDJSON catalog export for AI ingestion pipelines."""
    service = AiDiscoveryService(db)
    batch = await service.create_batch(requested_by=user.subject)
    async_result = generate_ai_export_task.delay(str(batch.id))
    return {"batch_id": str(batch.id), "task_id": async_result.id, "status": "queued"}


@router.get("/export/{batch_id}")
async def get_export_status(batch_id: str, db: DbSession) -> dict:
    service = AiDiscoveryService(db)
    batch = await service.get_batch(batch_id)
    if batch is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Batch not found")
    return {
        "id": str(batch.id),
        "status": batch.status.value,
        "record_count": batch.record_count,
        "checksum_sha256": batch.checksum_sha256,
        "completed_at": batch.completed_at,
        "error_message": batch.error_message,
    }


@router.get("/robots-ai.txt", response_class=Response)
async def get_ai_robots_directives() -> Response:
    """
    AI-agent-specific crawl directives, referenced from the main
    robots.txt. Points recognized AI crawlers at the bulk NDJSON export
    and the AI-specific sitemap, and rate-limits crawl frequency.
    """
    content = (
        "User-agent: GPTBot\n"
        "Allow: /ai-discovery/\n"
        "Crawl-delay: 2\n\n"
        "User-agent: Google-Extended\n"
        "Allow: /ai-discovery/\n"
        "Crawl-delay: 2\n\n"
        "Sitemap: /sitemaps/sitemap-index.xml\n"
    )
    return Response(content=content, media_type="text/plain")
