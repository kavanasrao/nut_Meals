"""
Manufacturing Reporting API.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.services.reporting_service import ReportingService

router = APIRouter(
    prefix="/reports",
    tags=["Manufacturing Reports"],
)


# ==========================================================
# DASHBOARD
# ==========================================================

@router.get("/dashboard")
async def dashboard(
    db: AsyncSession = Depends(get_db),
):

    service = ReportingService(db)

    return await service.dashboard()


# ==========================================================
# LOW STOCK
# ==========================================================

@router.get("/low-stock")
async def low_stock_materials(
    db: AsyncSession = Depends(get_db),
):

    service = ReportingService(db)

    return await service.low_stock_materials()


# ==========================================================
# ACTIVE BATCHES
# ==========================================================

@router.get("/active-batches")
async def active_batches(
    db: AsyncSession = Depends(get_db),
):

    service = ReportingService(db)

    return await service.active_batches()


# ==========================================================
# COMPLETED BATCHES
# ==========================================================

@router.get("/completed-batches")
async def completed_batches(
    db: AsyncSession = Depends(get_db),
):

    service = ReportingService(db)

    return await service.completed_batches()


# ==========================================================
# BATCH HISTORY
# ==========================================================

@router.get("/batch-history")
async def batch_history(
    db: AsyncSession = Depends(get_db),
):

    service = ReportingService(db)

    return await service.batch_history()

