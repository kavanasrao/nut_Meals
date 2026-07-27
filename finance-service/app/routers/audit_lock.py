from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.audit_lock import (
    PeriodLockCreate,
    PeriodLockResponse,
    PeriodUnlockRequest,
)
from app.services.audit_lock_service import AuditLockService

router = APIRouter(
    prefix="/audit-locks",
    tags=["Audit Locks"],
)


def get_audit_lock_service(
    db: AsyncSession = Depends(get_db),
) -> AuditLockService:
    return AuditLockService(db)


# =====================================================
# LOCK PERIOD
# =====================================================

@router.post(
    "/lock",
    response_model=PeriodLockResponse,
    status_code=status.HTTP_201_CREATED,
)
async def lock_period(
    payload: PeriodLockCreate,
    service: AuditLockService = Depends(get_audit_lock_service),
):
    return await service.lock_period(payload)


# =====================================================
# UNLOCK PERIOD
# =====================================================

@router.post(
    "/unlock/{period}",
    response_model=PeriodLockResponse,
)
async def unlock_period(
    period: str,
    payload: PeriodUnlockRequest,
    service: AuditLockService = Depends(get_audit_lock_service),
):
    return await service.unlock_period(
        period=period,
        unlocked_by=payload.unlocked_by,
        reason=payload.unlock_reason,
    )


# =====================================================
# GET PERIOD
# =====================================================

@router.get(
    "/{period}",
    response_model=PeriodLockResponse,
)
async def get_period(
    period: str,
    service: AuditLockService = Depends(get_audit_lock_service),
):
    lock = await service.get_period(period)

    if lock is None:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Accounting period not found.",
        )

    return lock


# =====================================================
# CHECK LOCK STATUS
# =====================================================

@router.get(
    "/{period}/status",
)
async def is_period_locked(
    period: str,
    service: AuditLockService = Depends(get_audit_lock_service),
):
    locked = await service.is_period_locked(period)

    return {
        "period": period,
        "locked": locked,
    }


# =====================================================
# LIST PERIODS
# =====================================================

@router.get(
    "/",
    response_model=list[PeriodLockResponse],
)
async def list_periods(
    service: AuditLockService = Depends(get_audit_lock_service),
):
    return await service.list_periods()


# =====================================================
# AUTO LOCK PREVIOUS MONTH
# =====================================================

@router.post(
    "/auto-lock",
    response_model=PeriodLockResponse,
)
async def auto_lock_previous_month(
    actor: str = "system",
    service: AuditLockService = Depends(get_audit_lock_service),
):
    return await service.auto_lock_previous_month(actor)


# =====================================================
# DELETE OPEN PERIOD
# =====================================================

@router.delete(
    "/{period}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_open_period(
    period: str,
    service: AuditLockService = Depends(get_audit_lock_service),
):
    await service.delete_open_period(period)