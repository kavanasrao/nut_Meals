"""Redirect manager endpoints: CRUD for admins + public resolution for frontend."""
import hashlib
import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import write_audit_log
from app.core.rbac import CurrentUser, Role, require_roles
from app.database import get_db
from app.schemas.redirect import (
    RedirectCreate,
    RedirectRead,
    RedirectResolveResponse,
    RedirectUpdate,
)
from app.services import redirect_service
from app.tasks.redirect_tasks import sync_redirect_analytics_task

router = APIRouter(prefix="/api/v1/redirects", tags=["redirects"])


def _hash_ip(request: Request) -> str | None:
    if not request.client:
        return None
    return hashlib.sha256(request.client.host.encode()).hexdigest()


@router.post("", response_model=RedirectRead, status_code=201)
async def create_redirect(
    payload: RedirectCreate,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles(Role.CATALOG_ADMIN)),
):
    redirect = await redirect_service.create_redirect(db, payload)
    await write_audit_log(
        db,
        actor_id=user.id,
        actor_role=user.role.value,
        action="redirect.create",
        resource_type="redirect",
        resource_id=str(redirect.id),
    )
    await db.commit()
    return redirect


@router.get("", response_model=list[RedirectRead])
async def list_redirects(
    active_only: bool = False,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles(Role.CATALOG_ADMIN, Role.VIEWER)),
):
    return await redirect_service.list_redirects(db, active_only=active_only)


@router.patch("/{redirect_id}", response_model=RedirectRead)
async def update_redirect(
    redirect_id: uuid.UUID,
    payload: RedirectUpdate,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles(Role.CATALOG_ADMIN)),
):
    redirect = await redirect_service.update_redirect(db, redirect_id, payload)
    await db.commit()
    return redirect


@router.delete("/{redirect_id}", status_code=204)
async def delete_redirect(
    redirect_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles(Role.CATALOG_ADMIN)),
):
    await redirect_service.delete_redirect(db, redirect_id)
    await db.commit()


@router.get("/resolve", response_model=RedirectResolveResponse)
async def resolve_redirect(path: str, request: Request, db: AsyncSession = Depends(get_db)):
    """Public endpoint the frontend/edge calls to resolve an old URL path.
    Logs usage and asynchronously syncs analytics via Celery."""
    redirect = await redirect_service.resolve_redirect(
        db,
        path,
        user_agent=request.headers.get("user-agent"),
        referrer=request.headers.get("referer"),
        ip_hash=_hash_ip(request),
    )
    await db.commit()
    if not redirect:
        return RedirectResolveResponse(found=False)

    sync_redirect_analytics_task.delay(str(redirect.id))
    return RedirectResolveResponse(
        found=True, target_path=redirect.target_path, redirect_type=redirect.redirect_type
    )
