"""
Public and internal sitemap endpoints.

Public GET endpoints serve pre-rendered XML so they can sit behind a
CDN cache (Cache-Control set generously since regeneration is
event-driven via Celery, not on-request). Rebuild triggers are
RBAC-protected and queue a Celery task rather than blocking.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.api.deps import DbSession
from app.core.security import CurrentUser, Role, require_roles
from app.models.sitemap import SitemapEntityType
from app.schemas.sitemap import SitemapRebuildAccepted, SitemapRebuildRequest
from app.services.sitemap_service import SitemapService
from app.tasks.sitemap_tasks import rebuild_sitemap_task

router = APIRouter(prefix="/sitemaps", tags=["sitemap"])

XML_MEDIA_TYPE = "application/xml"


@router.get("/sitemap-index.xml", response_class=Response)
async def get_sitemap_index(db: DbSession) -> Response:
    """Serve the top-level sitemap index referencing all sub-sitemaps."""
    service = SitemapService(db)
    sitemap_file = await service.get_file("sitemap-index.xml")
    if sitemap_file is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sitemap not generated yet")
    return Response(
        content=sitemap_file.xml_content,
        media_type=XML_MEDIA_TYPE,
        headers={"Cache-Control": "public, max-age=3600"},
    )


@router.get("/{file_name}", response_class=Response)
async def get_sitemap_file(file_name: str, db: DbSession) -> Response:
    """Serve a single paginated sitemap file, e.g. sitemap-products-1.xml."""
    if not file_name.endswith(".xml"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid file name")
    service = SitemapService(db)
    sitemap_file = await service.get_file(file_name)
    if sitemap_file is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sitemap file not found")
    return Response(
        content=sitemap_file.xml_content,
        media_type=XML_MEDIA_TYPE,
        headers={"Cache-Control": "public, max-age=3600"},
    )


@router.post(
    "/rebuild",
    response_model=SitemapRebuildAccepted,
    status_code=status.HTTP_202_ACCEPTED,
)
async def trigger_sitemap_rebuild(
    payload: SitemapRebuildRequest,
    user: Annotated[CurrentUser, Depends(require_roles(Role.SEO_EDITOR, Role.ADMIN))],
) -> SitemapRebuildAccepted:
    """Queue a Celery task to resync sitemap entries from Catalog/Blog and
    regenerate the affected XML file(s). Non-blocking by design."""
    entity_type_value = payload.entity_type.value if payload.entity_type else None
    async_result = rebuild_sitemap_task.delay(entity_type_value, payload.force)
    return SitemapRebuildAccepted(task_id=async_result.id, entity_type=entity_type_value)
