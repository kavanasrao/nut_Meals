"""
Pydantic schemas for accounting period locks.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# =====================================================
# ENUM
# =====================================================

class PeriodLockStatus(str, Enum):
    OPEN = "open"
    LOCKED = "locked"


# =====================================================
# BASE
# =====================================================

class PeriodLockBase(BaseModel):
    period: str = Field(..., pattern=r"^\d{4}-\d{2}$")


# =====================================================
# CREATE
# =====================================================

class PeriodLockCreate(PeriodLockBase):
    locked_by: Optional[str] = None
    lock_reason: Optional[str] = None


# =====================================================
# LOCK / UNLOCK REQUESTS
# =====================================================

class PeriodLockRequest(BaseModel):
    locked_by: str
    lock_reason: Optional[str] = None


class PeriodUnlockRequest(BaseModel):
    unlocked_by: str
    unlock_reason: str


# =====================================================
# RESPONSE
# =====================================================

class PeriodLockResponse(PeriodLockBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID

    status: PeriodLockStatus

    locked_by: Optional[str]
    locked_at: Optional[datetime]
    lock_reason: Optional[str]

    unlocked_by: Optional[str]
    unlocked_at: Optional[datetime]
    unlock_reason: Optional[str]

    created_at: datetime
    updated_at: datetime