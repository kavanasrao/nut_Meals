"""
Accounting Period Lock Service.

Responsible for:

- Locking accounting periods
- Unlocking periods
- Checking period status
- Automatic month-end locking
- Audit logging
"""

from datetime import datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from datetime import date, datetime, timedelta

from app.core.audit import AuditAction, write_audit_log
from app.models.audit_lock import (
    PeriodLock,
    PeriodLockStatus,
)
from app.schemas.audit_lock import (
    PeriodLockCreate,
    PeriodLockResponse,
)


class AuditLockService:

    def __init__(
        self,
        db: AsyncSession,
    ):
        self.db = db

    # =====================================================
    # GET PERIOD
    # =====================================================

    async def get_period(
        self,
        period: str,
    ) -> PeriodLock | None:

        return await self.db.scalar(
            select(PeriodLock).where(
                PeriodLock.period == period
            )
        )

    # =====================================================
    # IS LOCKED
    # =====================================================

    async def is_period_locked(
        self,
        period: str,
    ) -> bool:

        lock = await self.get_period(period)

        if lock is None:
            return False

        return lock.status == PeriodLockStatus.LOCKED

    # =====================================================
    # LOCK PERIOD
    # =====================================================

    async def lock_period(
        self,
        data: PeriodLockCreate,
    ) -> PeriodLock:

        existing = await self.get_period(
            data.period,
        )

        if existing:

            if existing.status == PeriodLockStatus.LOCKED:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Accounting period already locked.",
                )

            existing.status = PeriodLockStatus.LOCKED
            existing.locked_by = data.locked_by
            existing.lock_reason = data.lock_reason
            existing.locked_at = datetime.utcnow()

            await self.db.commit()
            await self.db.refresh(existing)

            lock = existing

        else:

            lock = PeriodLock(
                period=data.period,
                status=PeriodLockStatus.LOCKED,
                locked_by=data.locked_by,
                locked_at=datetime.utcnow(),
                lock_reason=data.lock_reason,
            )

            self.db.add(lock)

            await self.db.commit()
            await self.db.refresh(lock)

        await write_audit_log(
            db=self.db,
            entity_type="period_lock",
            entity_id=str(lock.id),
            action=AuditAction.PERIOD_LOCKED,
            actor=data.locked_by or "system",
            metadata={
                "period": lock.period,
            },
        )

        return lock
    


    # =====================================================
    # UNLOCK PERIOD
    # =====================================================

async def unlock_period(
        self,
        period: str,
        unlocked_by: str,
        reason: str,
    ) -> PeriodLock:

        lock = await self.get_period(period)

        if lock is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Accounting period not found.",
            )

        if lock.status == PeriodLockStatus.OPEN:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Accounting period is already open.",
            )

        lock.status = PeriodLockStatus.OPEN
        lock.unlocked_by = unlocked_by
        lock.unlocked_at = datetime.utcnow()
        lock.unlock_reason = reason

        await self.db.commit()
        await self.db.refresh(lock)

        await write_audit_log(
            db=self.db,
            entity_type="period_lock",
            entity_id=str(lock.id),
            action=AuditAction.PERIOD_UNLOCKED,
            actor=unlocked_by,
            metadata={
                "period": period,
                "reason": reason,
            },
        )

        return lock

    # =====================================================
    # AUTO LOCK PREVIOUS MONTH
    # =====================================================

async def auto_lock_previous_month(
        self,
        actor: str = "system",
    ) -> PeriodLock:

        today = date.today()
        first_day_this_month = today.replace(day=1)
        previous_month = first_day_this_month - timedelta(days=1)

        period = previous_month.strftime("%Y-%m")

        existing = await self.get_period(period)

        if existing:
            return existing

        lock = PeriodLock(
            period=period,
            status=PeriodLockStatus.LOCKED,
            locked_by=actor,
            locked_at=datetime.utcnow(),
            lock_reason="Automatic month-end lock",
        )

        self.db.add(lock)

        await self.db.commit()
        await self.db.refresh(lock)

        await write_audit_log(
            db=self.db,
            entity_type="period_lock",
            entity_id=str(lock.id),
            action=AuditAction.PERIOD_LOCKED,
            actor=actor,
            metadata={
                "period": period,
                "automatic": True,
            },
        )

        return lock

    # =====================================================
    # LIST PERIODS
    # =====================================================

async def list_periods(self) -> list[PeriodLock]:

        result = await self.db.execute(
            select(PeriodLock).order_by(
                PeriodLock.period.desc()
            )
        )

        return result.scalars().all()

    # =====================================================
    # DELETE OPEN PERIOD
    # =====================================================

async def delete_open_period(
        self,
        period: str,
    ) -> None:

        lock = await self.get_period(period)

        if lock is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Accounting period not found.",
            )

        if lock.status == PeriodLockStatus.LOCKED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Locked periods cannot be deleted.",
            )

        await self.db.delete(lock)
        await self.db.commit()