"""
Settlement schemas.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel

from app.models.settlement import SettlementStatus


class SettlementOut(BaseModel):
    id: UUID
    gateway: str
    settlement_reference: str
    amount: Decimal
    currency: str
    status: SettlementStatus
    settlement_date: datetime
    gateway_report: Optional[dict] = None

    model_config = {
        "from_attributes": True
    }