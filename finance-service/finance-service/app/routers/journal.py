"""Journal entry endpoints - creation, posting, reversal, retrieval."""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import FinanceRole, Principal, require_roles
from app.models.journal import JournalEntryStatus
from app.schemas.journal import JournalEntryCreate, JournalEntryOut, JournalEntryReverseRequest
from app.services.journal_service import JournalService

router = APIRouter(prefix="/journal/entries", tags=["Journal Entries"])


@router.post("", response_model=JournalEntryOut, status_code=201)
async def create_journal_entry(
    payload: JournalEntryCreate,
    auto_post: bool = Query(True, description="Immediately post the entry after creation"),
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_roles(FinanceRole.ACCOUNTANT)),
):
    """
    Creates a balanced double-entry journal entry. Pydantic validation
    guarantees debits == credits before this handler even runs; the service
    layer re-validates and performs the atomic DB write.
    """
    service = JournalService(db)
    return await service.create_and_post_entry(payload, actor=principal.subject, auto_post=auto_post)


@router.get("", response_model=list[JournalEntryOut])
async def list_journal_entries(
    status_filter: JournalEntryStatus | None = Query(None, alias="status"),
    source_reference: str | None = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_roles(FinanceRole.VIEWER)),
):
    service = JournalService(db)
    return await service.list_entries(
        status_filter=status_filter, source_reference=source_reference, limit=limit, offset=offset
    )


@router.get("/{entry_id}", response_model=JournalEntryOut)
async def get_journal_entry(
    entry_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_roles(FinanceRole.VIEWER)),
):
    service = JournalService(db)
    return await service.get_entry(entry_id)


@router.post("/{entry_id}/post", response_model=JournalEntryOut)
async def post_journal_entry(
    entry_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_roles(FinanceRole.ACCOUNTANT)),
):
    """Posts a DRAFT entry, making it permanent and included in balances/reports."""
    service = JournalService(db)
    return await service.post_entry(entry_id, actor=principal.subject)


@router.post("/{entry_id}/reverse", response_model=JournalEntryOut)
async def reverse_journal_entry(
    entry_id: uuid.UUID,
    payload: JournalEntryReverseRequest,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_roles(FinanceRole.ACCOUNTANT)),
):
    """Reverses a POSTED entry via a new offsetting entry (immutable audit trail)."""
    service = JournalService(db)
    return await service.reverse_entry(entry_id, actor=principal.subject, reason=payload.reason)
