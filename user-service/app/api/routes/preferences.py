"""Customer preference routes (language, dark mode, marketing opt-in).

GET   /api/v1/preferences  — get my preferences (created with defaults if absent)
PATCH /api/v1/preferences  — update my preferences
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_active_user
from app.core.db import get_db
from app.models.audit_log import AuditAction
from app.models.user import User
from app.schemas.preference import PreferenceOut, PreferenceUpdate
from app.services.audit_service import AuditService
from app.services.preference_service import PreferenceService

router = APIRouter(prefix="/preferences", tags=["preferences"])


@router.get("", response_model=PreferenceOut, summary="Get my preferences")
async def get_preferences(
    db: AsyncSession = Depends(get_db), user: User = Depends(require_active_user)
) -> PreferenceOut:
    svc = PreferenceService(db)
    pref = await svc.get_or_create(user.id)
    return PreferenceOut.model_validate(pref)


@router.patch("", response_model=PreferenceOut, summary="Update my preferences")
async def update_preferences(
    body: PreferenceUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_active_user),
) -> PreferenceOut:
    svc = PreferenceService(db)
    pref = await svc.update(user.id, body)
    await AuditService(db).record(
        user_id=user.id,
        action=AuditAction.PREFERENCE_UPDATE,
        description="Updated preferences",
        extra_data=body.model_dump(exclude_unset=True),
    )
    return PreferenceOut.model_validate(pref)
