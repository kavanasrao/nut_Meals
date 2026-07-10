"""Business logic for Returns Management."""
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.common import ReturnStatus
from app.models.returns import ReturnEvent, ReturnRequest
from app.schemas.returns import ReturnDecisionRequest
from app.services.logistics_client import LogisticsServiceClient


async def get_return_request(db: AsyncSession, return_id: uuid.UUID) -> ReturnRequest:
    ret = await db.get(ReturnRequest, return_id)
    if ret is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Return request not found")
    return ret


async def list_return_requests(
    db: AsyncSession,
    *,
    status_filter: Optional[ReturnStatus] = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[ReturnRequest], int]:
    query = select(ReturnRequest)
    count_query = select(func.count()).select_from(ReturnRequest)

    if status_filter is not None:
        query = query.where(ReturnRequest.status == status_filter)
        count_query = count_query.where(ReturnRequest.status == status_filter)

    total = (await db.execute(count_query)).scalar_one()
    query = query.order_by(ReturnRequest.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    items = (await db.execute(query)).scalars().all()
    return list(items), total


async def _transition(
    db: AsyncSession,
    *,
    ret: ReturnRequest,
    to_status: ReturnStatus,
    actor_admin_id: uuid.UUID,
    notes: Optional[str],
) -> ReturnRequest:
    if ret.status in (ReturnStatus.APPROVED, ReturnStatus.REJECTED, ReturnStatus.RESOLVED) and to_status not in (
        ReturnStatus.RESOLVED,
    ):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail=f"Return request is already {ret.status.value} and cannot be re-decided",
        )

    event = ReturnEvent(
        return_request_id=ret.id,
        from_status=ret.status,
        to_status=to_status,
        actor_admin_id=actor_admin_id,
        notes=notes,
    )
    db.add(event)

    ret.status = to_status
    ret.decided_by_admin_id = actor_admin_id
    ret.decided_at = datetime.now(timezone.utc)
    if notes:
        ret.resolution_notes = notes

    await db.flush()
    await db.refresh(ret)
    return ret


async def approve_return(
    db: AsyncSession,
    *,
    return_id: uuid.UUID,
    decision: ReturnDecisionRequest,
    actor_admin_id: uuid.UUID,
    logistics_client: LogisticsServiceClient,
) -> ReturnRequest:
    ret = await get_return_request(db, return_id)
    ret.tier = decision.tier
    ret.refund_amount = decision.refund_amount
    ret.restock_required = decision.restock_required

    ret = await _transition(
        db,
        ret=ret,
        to_status=ReturnStatus.APPROVED,
        actor_admin_id=actor_admin_id,
        notes=decision.resolution_notes,
    )

    if ret.restock_required:
        # Kick off reverse logistics; failure here should not roll back the
        # approval decision itself, so we surface it but don't raise.
        try:
            pickup = await logistics_client.schedule_return_pickup(ret.order_id, ret.id)
            ret.logistics_reference = pickup.get("reference")
            await db.flush()
        except Exception:
            # In production this would emit a metric/alert for manual follow-up.
            pass

    return ret


async def reject_return(
    db: AsyncSession,
    *,
    return_id: uuid.UUID,
    decision: ReturnDecisionRequest,
    actor_admin_id: uuid.UUID,
) -> ReturnRequest:
    ret = await get_return_request(db, return_id)
    ret.tier = decision.tier
    return await _transition(
        db,
        ret=ret,
        to_status=ReturnStatus.REJECTED,
        actor_admin_id=actor_admin_id,
        notes=decision.resolution_notes,
    )


async def resolve_return(
    db: AsyncSession,
    *,
    return_id: uuid.UUID,
    actor_admin_id: uuid.UUID,
    notes: Optional[str] = None,
) -> ReturnRequest:
    """Mark a return fully resolved (refund issued / restock complete)."""
    ret = await get_return_request(db, return_id)
    return await _transition(
        db, ret=ret, to_status=ReturnStatus.RESOLVED, actor_admin_id=actor_admin_id, notes=notes
    )
