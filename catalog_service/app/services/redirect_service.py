"""Business logic for the redirect manager."""
import uuid
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.redirect import Redirect, RedirectLog
from app.schemas.redirect import RedirectCreate, RedirectUpdate


async def create_redirect(db: AsyncSession, payload: RedirectCreate) -> Redirect:
    existing = await db.execute(select(Redirect).where(Redirect.source_path == payload.source_path))
    if existing.scalar_one_or_none():
        raise HTTPException(status.HTTP_409_CONFLICT, detail="A redirect for this source_path already exists")
    redirect = Redirect(**payload.model_dump())
    db.add(redirect)
    await db.flush()
    await db.refresh(redirect)
    return redirect


async def get_redirect(db: AsyncSession, redirect_id: uuid.UUID) -> Redirect:
    result = await db.execute(select(Redirect).where(Redirect.id == redirect_id))
    redirect = result.scalar_one_or_none()
    if not redirect:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Redirect not found")
    return redirect


async def list_redirects(db: AsyncSession, active_only: bool = False) -> list[Redirect]:
    query = select(Redirect)
    if active_only:
        query = query.where(Redirect.is_active.is_(True))
    result = await db.execute(query.order_by(Redirect.created_at.desc()))
    return list(result.scalars().all())


async def update_redirect(db: AsyncSession, redirect_id: uuid.UUID, payload: RedirectUpdate) -> Redirect:
    redirect = await get_redirect(db, redirect_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(redirect, field, value)
    await db.flush()
    await db.refresh(redirect)
    return redirect


async def delete_redirect(db: AsyncSession, redirect_id: uuid.UUID) -> None:
    redirect = await get_redirect(db, redirect_id)
    await db.delete(redirect)
    await db.flush()


async def resolve_redirect(
    db: AsyncSession,
    source_path: str,
    *,
    user_agent: Optional[str] = None,
    referrer: Optional[str] = None,
    ip_hash: Optional[str] = None,
) -> Optional[Redirect]:
    """Look up an active redirect for the given path and record a usage log entry.

    Logging is done inline (fast, single insert) — heavier analytics rollups
    are handled asynchronously by the Celery redirect_sync task.
    """
    result = await db.execute(
        select(Redirect).where(Redirect.source_path == source_path, Redirect.is_active.is_(True))
    )
    redirect = result.scalar_one_or_none()
    if redirect:
        db.add(
            RedirectLog(
                redirect_id=redirect.id, user_agent=user_agent, referrer=referrer, ip_hash=ip_hash
            )
        )
        await db.flush()
    return redirect
