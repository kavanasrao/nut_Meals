"""Dashboard route — aggregate stats from all services."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.auth.dependencies import require_admin
from app.models.models import AdminUser
from app.schemas.schemas import DashboardStats
from app.services.dashboard_service import DashboardService

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get(
    "/",
    response_model=DashboardStats,
    summary="Get aggregated system stats for the admin dashboard",
)
async def get_dashboard(
    current_admin: AdminUser = Depends(require_admin),
) -> DashboardStats:
    """
    Fans out to all downstream services concurrently.
    Partial failures are handled gracefully (returns 0/unknown for unavailable services).
    """
    svc = DashboardService()
    return await svc.get_stats()
