"""
Structured data endpoints: expose cached schema.org JSON-LD for
frontend server-side rendering (so the frontend can inline a
<script type="application/ld+json"> tag), and trigger resync for a
single entity when it changes.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import DbSession
from app.core.security import CurrentUser, Role, require_roles
from app.models.structured_data import SchemaType
from app.schemas.structured_data import StructuredDataOut, StructuredDataSyncRequest
from app.services.structured_data_service import StructuredDataService
from app.tasks.schema_sync_tasks import sync_structured_data_task

router = APIRouter(prefix="/structured-data", tags=["structured-data"])


@router.get("/products/{product_id}", response_model=StructuredDataOut)
async def get_product_structured_data(product_id: str, db: DbSession) -> StructuredDataOut:
    service = StructuredDataService(db)
    record = await service.get_record("product", product_id, SchemaType.PRODUCT)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Structured data not yet generated for this product",
        )
    return StructuredDataOut.model_validate(record)


@router.get("/blog-posts/{post_id}", response_model=StructuredDataOut)
async def get_blog_post_structured_data(post_id: str, db: DbSession) -> StructuredDataOut:
    service = StructuredDataService(db)
    record = await service.get_record("blog_post", post_id, SchemaType.BLOG_POSTING)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Structured data not yet generated for this blog post",
        )
    return StructuredDataOut.model_validate(record)


@router.post("/sync", status_code=status.HTTP_202_ACCEPTED)
async def sync_structured_data(
    payload: StructuredDataSyncRequest,
    user: Annotated[CurrentUser, Depends(require_roles(Role.SEO_EDITOR, Role.ADMIN))],
) -> dict:
    """Queue a resync of JSON-LD for a single entity (e.g. after a price change)."""
    async_result = sync_structured_data_task.delay(payload.entity_type, payload.entity_id)
    return {"task_id": async_result.id, "status": "queued"}
