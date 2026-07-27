from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from uuid import UUID

from app.core.database import get_db
from app.schemas.credit_note import (
    CreditNoteCreate,
    CreditNoteUpdate,
    CreditNoteResponse,
)
from app.services.credit_note_service import CreditNoteService

router = APIRouter(
    prefix="/credit-notes",
    tags=["Credit Notes"],
)


def get_credit_note_service(
    db: AsyncSession = Depends(get_db),
) -> CreditNoteService:
    return CreditNoteService(db)


# =====================================================
# CREATE
# =====================================================

@router.post(
    "/",
    response_model=CreditNoteResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_credit_note(
    payload: CreditNoteCreate,
    service: CreditNoteService = Depends(get_credit_note_service),
):
    return await service.create_credit_note(payload)


# =====================================================
# GET
# =====================================================

@router.get(
    "/",
    response_model=list[CreditNoteResponse],
)
async def list_credit_notes(
    service: CreditNoteService = Depends(get_credit_note_service),
):
    return await service.list_credit_notes()


@router.get(
    "/{credit_note_id}",
    response_model=CreditNoteResponse,
)
async def get_credit_note(
    credit_note_id: UUID,
    service: CreditNoteService = Depends(get_credit_note_service),
):
    return await service.get_credit_note(
        credit_note_id
    )


@router.get(
    "/number/{credit_note_number}",
    response_model=CreditNoteResponse,
)
async def get_credit_note_by_number(
    credit_note_number: str,
    service: CreditNoteService = Depends(get_credit_note_service),
):
    return await service.get_credit_note_by_number(
        credit_note_number
    )


@router.get(
    "/status/{status}",
    response_model=list[CreditNoteResponse],
)
async def list_by_status(
    status: str,
    service: CreditNoteService = Depends(get_credit_note_service),
):
    return await service.list_by_status(status)



# =====================================================
# UPDATE
# =====================================================

@router.put(
    "/{credit_note_id}",
    response_model=CreditNoteResponse,
)
async def update_credit_note(
    credit_note_id: UUID,
    payload: CreditNoteUpdate,
    service: CreditNoteService = Depends(get_credit_note_service),
):
    return await service.update_credit_note(
        credit_note_id,
        payload,
    )


# =====================================================
# ISSUE
# =====================================================

@router.post(
    "/{credit_note_id}/issue",
    response_model=CreditNoteResponse,
)
async def issue_credit_note(
    credit_note_id: UUID,
    issued_by: str,
    service: CreditNoteService = Depends(get_credit_note_service),
):
    return await service.issue_credit_note(
        credit_note_id,
        issued_by,
    )


# =====================================================
# APPLY REFUND
# =====================================================

@router.post(
    "/{credit_note_id}/apply-refund",
    response_model=CreditNoteResponse,
)
async def apply_refund(
    credit_note_id: UUID,
    refund_id: UUID,
    applied_by: str,
    service: CreditNoteService = Depends(get_credit_note_service),
):
    return await service.apply_refund(
        credit_note_id,
        refund_id,
        applied_by,
    )


# =====================================================
# CANCEL
# =====================================================

@router.post(
    "/{credit_note_id}/cancel",
    response_model=CreditNoteResponse,
)
async def cancel_credit_note(
    credit_note_id: UUID,
    cancelled_by: str,
    reason: str | None = None,
    service: CreditNoteService = Depends(get_credit_note_service),
):
    return await service.cancel_credit_note(
        credit_note_id,
        cancelled_by,
        reason,
    )


# =====================================================
# DELETE
# =====================================================

@router.delete(
    "/{credit_note_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_credit_note(
    credit_note_id: UUID,
    service: CreditNoteService = Depends(get_credit_note_service),
):
    await service.delete_draft_credit_note(
        credit_note_id
    )