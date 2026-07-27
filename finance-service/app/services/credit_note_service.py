"""
Credit Note Service.

Responsible for:

- Draft credit notes
- Issue credit notes
- Journal reversal
- Refund linking
- Audit logging
"""

from datetime import datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import AuditAction, write_audit_log
from app.models.audit_lock import PeriodLock, PeriodLockStatus
from app.services.journal_service import JournalService

from app.models.credit_note import (
    CreditNote,
    CreditNoteStatus,
)
from app.models.gst import GSTInvoice
from app.schemas.credit_note import (
    CreditNoteCreate,
    CreditNoteUpdate,
)


class CreditNoteService:

    def __init__(
        self,
        db: AsyncSession,
    ):
        self.db = db

    # =====================================================
    # CREATE DRAFT
    # =====================================================

    async def create_credit_note(
        self,
        data: CreditNoteCreate,
    ) -> CreditNote:

        invoice = None

        if data.gst_invoice_id:

            invoice = await self.db.get(
                GSTInvoice,
                data.gst_invoice_id,
            )

            if invoice is None:
                raise HTTPException(
                    status_code=404,
                    detail="GST invoice not found.",
                )

        credit_note = CreditNote(
            **data.model_dump(),
            status=CreditNoteStatus.DRAFT,
        )

        self.db.add(credit_note)

        try:

            await self.db.commit()
            await self.db.refresh(credit_note)

            return credit_note

        except SQLAlchemyError:

            await self.db.rollback()

            raise HTTPException(
                status_code=500,
                detail="Unable to create credit note.",
            )

    # =====================================================
    # GET
    # =====================================================

    async def get_credit_note(
        self,
        credit_note_id: UUID,
    ) -> CreditNote:

        note = await self.db.get(
            CreditNote,
            credit_note_id,
        )

        if note is None:
            raise HTTPException(
                status_code=404,
                detail="Credit note not found.",
            )

        return note

    # =====================================================
    # LIST
    # =====================================================

    async def list_credit_notes(
        self,
    ) -> list[CreditNote]:

        result = await self.db.execute(
            select(CreditNote).order_by(
                CreditNote.created_at.desc()
            )
        )

        return result.scalars().all()
    


    # =====================================================
    # PERIOD LOCK
    # =====================================================

async def _ensure_period_open(self, invoice_date):

        period = invoice_date.strftime("%Y-%m")

        lock = await self.db.scalar(
            select(PeriodLock).where(
                PeriodLock.period == period
            )
        )

        if (
            lock
            and lock.status == PeriodLockStatus.LOCKED
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Accounting period {period} is locked.",
            )

    # =====================================================
    # ISSUE CREDIT NOTE
    # =====================================================

async def issue_credit_note(
        self,
        credit_note_id: UUID,
        issued_by: str,
    ) -> CreditNote:

        note = await self.get_credit_note(
            credit_note_id
        )

        if note.status != CreditNoteStatus.DRAFT:
            raise HTTPException(
                status_code=409,
                detail="Only draft credit notes can be issued.",
            )

        if note.gst_invoice is None:
            raise HTTPException(
                status_code=400,
                detail="Credit note is not linked to a GST invoice.",
            )

        await self._ensure_period_open(
            note.gst_invoice.invoice_date
        )

        journal_service = JournalService(self.db)

        journal = await journal_service.create_credit_note_entry(
            credit_note=note,
            issued_by=issued_by,
        )

        note.status = CreditNoteStatus.ISSUED
        note.journal_entry_id = journal.id
        note.issued_by = issued_by
        note.issued_at = datetime.utcnow()

        await self.db.commit()
        await self.db.refresh(note)

        await write_audit_log(
            db=self.db,
            entity_type="credit_note",
            entity_id=str(note.id),
            action=AuditAction.CREATED,
            actor=issued_by,
            metadata={
                "credit_note_number": note.credit_note_number,
                "journal_entry": str(journal.id),
            },
        )

        return note

    # =====================================================
    # UPDATE DRAFT
    # =====================================================

async def update_credit_note(
        self,
        credit_note_id: UUID,
        data: CreditNoteUpdate,
    ) -> CreditNote:

        note = await self.get_credit_note(
            credit_note_id,
        )

        if note.status != CreditNoteStatus.DRAFT:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Only draft credit notes can be updated.",
            )

        for key, value in data.model_dump(
            exclude_unset=True
        ).items():
            setattr(note, key, value)

        await self.db.commit()
        await self.db.refresh(note)

        return note

    # =====================================================
    # APPLY REFUND
    # =====================================================

async def apply_refund(
        self,
        credit_note_id: UUID,
        refund_id: UUID,
        applied_by: str,
    ) -> CreditNote:

        note = await self.get_credit_note(
            credit_note_id,
        )

        if note.status != CreditNoteStatus.ISSUED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Only issued credit notes can be applied.",
            )

        note.refund_id = refund_id
        note.status = CreditNoteStatus.APPLIED

        await self.db.commit()
        await self.db.refresh(note)

        await write_audit_log(
            db=self.db,
            entity_type="credit_note",
            entity_id=str(note.id),
            action=AuditAction.UPDATED,
            actor=applied_by,
            metadata={
                "refund_id": str(refund_id),
                "status": "applied",
            },
        )

        return note

    # =====================================================
    # CANCEL DRAFT
    # =====================================================

async def cancel_credit_note(
        self,
        credit_note_id: UUID,
        cancelled_by: str,
        reason: str | None = None,
    ) -> CreditNote:

        note = await self.get_credit_note(
            credit_note_id,
        )

        if note.status != CreditNoteStatus.DRAFT:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Only draft credit notes can be cancelled.",
            )

        note.status = CreditNoteStatus.CANCELLED

        if reason:
            note.notes = (
                f"{note.notes or ''}\nCancelled: {reason}"
            ).strip()

        await self.db.commit()
        await self.db.refresh(note)

        await write_audit_log(
            db=self.db,
            entity_type="credit_note",
            entity_id=str(note.id),
            action=AuditAction.UPDATED,
            actor=cancelled_by,
            metadata={
                "status": "cancelled",
                "reason": reason,
            },
        )

        return note

    # =====================================================
    # QUERY HELPERS
    # =====================================================

async def get_credit_note_by_number(
        self,
        credit_note_number: str,
    ) -> CreditNote:

        note = await self.db.scalar(
            select(CreditNote).where(
                CreditNote.credit_note_number == credit_note_number
            )
        )

        if note is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Credit note not found.",
            )

        return note

async def list_by_status(
        self,
        status: CreditNoteStatus,
    ) -> list[CreditNote]:

        result = await self.db.execute(
            select(CreditNote)
            .where(CreditNote.status == status)
            .order_by(CreditNote.created_at.desc())
        )

        return result.scalars().all()

async def delete_draft_credit_note(
        self,
        credit_note_id: UUID,
    ) -> None:

        note = await self.get_credit_note(
            credit_note_id,
        )

        if note.status != CreditNoteStatus.DRAFT:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Only draft credit notes can be deleted.",
            )

        await self.db.delete(note)
        await self.db.commit()

async def list_credit_notes_by_order(
        self,
        order_reference: str,
    ) -> list[CreditNote]:

        result = await self.db.execute(
            select(CreditNote)
            .where(
                CreditNote.order_reference == order_reference
            )
            .order_by(CreditNote.created_at.desc())
        )

        return result.scalars().all()

async def list_credit_notes_by_invoice(
        self,
        gst_invoice_id: UUID,
    ) -> list[CreditNote]:

        result = await self.db.execute(
            select(CreditNote)
            .where(
                CreditNote.gst_invoice_id == gst_invoice_id
            )
            .order_by(CreditNote.created_at.desc())
        )

        return result.scalars().all()