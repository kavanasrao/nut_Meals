"""
Manufacturing Audit API.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.services.manufacturing_audit_service import (
    ManufacturingAuditService,
)

router = APIRouter(
    prefix="/audit",
    tags=["Manufacturing Audit"],
)


# ==========================================================
# LIST
# ==========================================================

@router.get("/")
async def list_audits(
    db: AsyncSession = Depends(get_db),
):

    service = ManufacturingAuditService(db)

    return await service.list()


# ==========================================================
# GET
# ==========================================================

@router.get("/{audit_id}")
async def get_audit(
    audit_id: UUID,
    db: AsyncSession = Depends(get_db),
):

    service = ManufacturingAuditService(db)

    audit = await service.get(audit_id)

    if audit is None:
        raise HTTPException(
            status_code=404,
            detail="Audit record not found",
        )

    return audit


# ==========================================================
# ENTITY HISTORY
# ==========================================================

@router.get("/entity/{entity_type}/{entity_id}")
async def entity_history(
    entity_type: str,
    entity_id: str,
    db: AsyncSession = Depends(get_db),
):

    service = ManufacturingAuditService(db)

    return await service.get_by_entity(
        entity_type,
        entity_id,
    )


# ==========================================================
# USER HISTORY
# ==========================================================

@router.get("/user/{user_id}")
async def user_history(
    user_id: str,
    db: AsyncSession = Depends(get_db),
):

    service = ManufacturingAuditService(db)

    return await service.get_by_user(user_id)
