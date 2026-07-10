"""
API routes for the Content/Blog Manager: CRUD for blog posts, announcements,
and FAQs, with SEO metadata and scheduling.
"""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_audit_event
from app.core.security import AdminPrincipal, require_roles
from app.database import get_db
from app.models.common import AdminRole, ContentStatus, ContentType
from app.schemas.content import (
    ContentItemCreate,
    ContentItemListResponse,
    ContentItemResponse,
    ContentItemUpdate,
)
from app.services import content_service

router = APIRouter(prefix="/api/v1/content", tags=["content"])

_WRITE_ROLES = (AdminRole.SUPER_ADMIN, AdminRole.CONTENT_ADMIN)
_READ_ROLES = (AdminRole.SUPER_ADMIN, AdminRole.CONTENT_ADMIN, AdminRole.ANALYTICS_VIEWER)


@router.post("", response_model=ContentItemResponse, status_code=status.HTTP_201_CREATED)
async def create_content_item(
    payload: ContentItemCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: AdminPrincipal = Depends(require_roles(*_WRITE_ROLES)),
) -> ContentItemResponse:
    """Create a new blog post, announcement, or FAQ entry."""
    item = await content_service.create_content_item(db, data=payload, author_admin_id=admin.admin_id)
    await record_audit_event(
        db,
        actor=admin,
        action="content.create",
        resource_type="content_item",
        resource_id=str(item.id),
        request_ip=request.client.host if request.client else None,
    )
    await db.commit()
    return ContentItemResponse.model_validate(item)


@router.get("", response_model=ContentItemListResponse)
async def list_content_items(
    content_type: Optional[ContentType] = None,
    status_filter: Optional[ContentStatus] = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    admin: AdminPrincipal = Depends(require_roles(*_READ_ROLES)),
) -> ContentItemListResponse:
    """List content items, optionally filtered by type and status."""
    items, total = await content_service.list_content_items(
        db, content_type=content_type, status_filter=status_filter, page=page, page_size=page_size
    )
    return ContentItemListResponse(
        items=[ContentItemResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{content_id}", response_model=ContentItemResponse)
async def get_content_item(
    content_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    admin: AdminPrincipal = Depends(require_roles(*_READ_ROLES)),
) -> ContentItemResponse:
    item = await content_service.get_content_item(db, content_id)
    return ContentItemResponse.model_validate(item)


@router.patch("/{content_id}", response_model=ContentItemResponse)
async def update_content_item(
    content_id: uuid.UUID,
    payload: ContentItemUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: AdminPrincipal = Depends(require_roles(*_WRITE_ROLES)),
) -> ContentItemResponse:
    """Update a content item. Records a revision snapshot of the prior version."""
    item = await content_service.update_content_item(
        db, content_id=content_id, data=payload, editor_admin_id=admin.admin_id
    )
    await record_audit_event(
        db,
        actor=admin,
        action="content.update",
        resource_type="content_item",
        resource_id=str(content_id),
        request_ip=request.client.host if request.client else None,
    )
    await db.commit()
    return ContentItemResponse.model_validate(item)


@router.post("/{content_id}/publish", response_model=ContentItemResponse)
async def publish_content_item(
    content_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: AdminPrincipal = Depends(require_roles(*_WRITE_ROLES)),
) -> ContentItemResponse:
    """Immediately publish a content item, bypassing any schedule."""
    item = await content_service.publish_content_item(db, content_id=content_id)
    await record_audit_event(
        db,
        actor=admin,
        action="content.publish",
        resource_type="content_item",
        resource_id=str(content_id),
        request_ip=request.client.host if request.client else None,
    )
    await db.commit()
    return ContentItemResponse.model_validate(item)


@router.post("/{content_id}/archive", response_model=ContentItemResponse)
async def archive_content_item(
    content_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: AdminPrincipal = Depends(require_roles(*_WRITE_ROLES)),
) -> ContentItemResponse:
    item = await content_service.archive_content_item(db, content_id=content_id)
    await record_audit_event(
        db,
        actor=admin,
        action="content.archive",
        resource_type="content_item",
        resource_id=str(content_id),
        request_ip=request.client.host if request.client else None,
    )
    await db.commit()
    return ContentItemResponse.model_validate(item)


@router.delete("/{content_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_content_item(
    content_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: AdminPrincipal = Depends(require_roles(AdminRole.SUPER_ADMIN, AdminRole.CONTENT_ADMIN)),
) -> None:
    await content_service.delete_content_item(db, content_id=content_id)
    await record_audit_event(
        db,
        actor=admin,
        action="content.delete",
        resource_type="content_item",
        resource_id=str(content_id),
        request_ip=request.client.host if request.client else None,
    )
    await db.commit()
