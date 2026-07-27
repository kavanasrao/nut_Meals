"""
Refund Service.

Responsible for:

- Refund creation
- Refund processing
- Journal posting
- Credit Note linking
- Audit logging
"""

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from datetime import datetime

from app.core.audit import AuditAction, write_audit_log
from app.services.journal_service import JournalService

from app.models.credit_note import (
    CreditNote,
    CreditNoteStatus,
)
from app.models.refund import (
    Refund,
    RefundStatus,
)
from app.schemas.refund import (
    RefundCreate,
    RefundUpdate,
)


class RefundService:

    def __init__(
        self,
        db: AsyncSession,
    ):
        self.db = db

    # =====================================================
    # CREATE
    # =====================================================

    async def create_refund(
        self,
        data: RefundCreate,
    ) -> Refund:

        credit_note = await self.db.get(
            CreditNote,
            data.credit_note_id,
        )

        if credit_note is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Credit note not found.",
            )

        if credit_note.status != CreditNoteStatus.ISSUED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Refund can only be created for an issued credit note.",
            )

        refund = Refund(
            **data.model_dump(),
            status=RefundStatus.PENDING,
        )

        self.db.add(refund)

        try:
            await self.db.commit()
            await self.db.refresh(refund)

            return refund

        except SQLAlchemyError:
            await self.db.rollback()

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Unable to create refund.",
            )

    # =====================================================
    # GET
    # =====================================================

    async def get_refund(
        self,
        refund_id: UUID,
    ) -> Refund:

        refund = await self.db.get(
            Refund,
            refund_id,
        )

        if refund is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Refund not found.",
            )

        return refund

    # =====================================================
    # LIST
    # =====================================================

    async def list_refunds(
        self,
    ) -> list[Refund]:

        result = await self.db.execute(
            select(Refund).order_by(
                Refund.created_at.desc()
            )
        )

        return result.scalars().all()
    


    # =====================================================
    # PROCESS REFUND
    # =====================================================

async def process_refund(
        self,
        refund_id: UUID,
        gateway_refund_id: str,
        processed_by: str,
    ) -> Refund:

        refund = await self.get_refund(
            refund_id,
        )

        if refund.status != RefundStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Only pending refunds can be processed.",
            )

        journal_service = JournalService(self.db)

        journal = await journal_service.create_refund_entry(
            refund=refund,
            processed_by=processed_by,
        )

        refund.status = RefundStatus.COMPLETED
        refund.gateway_refund_id = gateway_refund_id
        refund.completed_at = datetime.utcnow()
        refund.journal_entry_id = journal.id

        credit_note = await self.db.scalar(
            select(CreditNote).where(
                CreditNote.refund_id == refund.id
            )
        )

        if credit_note:
            credit_note.status = CreditNoteStatus.APPLIED

        await self.db.commit()
        await self.db.refresh(refund)

        await write_audit_log(
            db=self.db,
            entity_type="refund",
            entity_id=str(refund.id),
            action=AuditAction.UPDATED,
            actor=processed_by,
            metadata={
                "status": "completed",
                "gateway_refund_id": gateway_refund_id,
                "journal_entry": str(journal.id),
            },
        )

        return refund

    # =====================================================
    # FAIL REFUND
    # =====================================================

async def fail_refund(
        self,
        refund_id: UUID,
        reason: str,
        processed_by: str,
    ) -> Refund:

        refund = await self.get_refund(
            refund_id,
        )

        if refund.status != RefundStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Only pending refunds can be failed.",
            )

        refund.status = RefundStatus.FAILED
        refund.reason = reason

        await self.db.commit()
        await self.db.refresh(refund)

        await write_audit_log(
            db=self.db,
            entity_type="refund",
            entity_id=str(refund.id),
            action=AuditAction.UPDATED,
            actor=processed_by,
            metadata={
                "status": "failed",
                "reason": reason,
            },
        )

        return refund

    # =====================================================
    # UPDATE
    # =====================================================

async def update_refund(
        self,
        refund_id: UUID,
        data: RefundUpdate,
    ) -> Refund:

        refund = await self.get_refund(
            refund_id,
        )

        if refund.status == RefundStatus.COMPLETED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Completed refunds cannot be modified.",
            )

        for key, value in data.model_dump(
            exclude_unset=True
        ).items():
            setattr(refund, key, value)

        await self.db.commit()
        await self.db.refresh(refund)

        return refund

    # =====================================================
    # CANCEL
    # =====================================================

async def cancel_refund(
        self,
        refund_id: UUID,
        cancelled_by: str,
        reason: str | None = None,
    ) -> Refund:

        refund = await self.get_refund(
            refund_id,
        )

        if refund.status == RefundStatus.COMPLETED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Completed refunds cannot be cancelled.",
            )

        refund.status = RefundStatus.CANCELLED

        if reason:
            refund.reason = reason

        await self.db.commit()
        await self.db.refresh(refund)

        await write_audit_log(
            db=self.db,
            entity_type="refund",
            entity_id=str(refund.id),
            action=AuditAction.UPDATED,
            actor=cancelled_by,
            metadata={
                "status": "cancelled",
                "reason": reason,
            },
        )

        return refund

    # =====================================================
    # QUERY HELPERS
    # =====================================================

async def get_refund_by_gateway_id(
        self,
        gateway_refund_id: str,
    ) -> Refund:

        refund = await self.db.scalar(
            select(Refund).where(
                Refund.gateway_refund_id == gateway_refund_id
            )
        )

        if refund is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Refund not found.",
            )

        return refund

async def list_refunds_by_status(
        self,
        status: RefundStatus,
    ) -> list[Refund]:

        result = await self.db.execute(
            select(Refund)
            .where(Refund.status == status)
            .order_by(Refund.created_at.desc())
        )

        return result.scalars().all()

async def list_refunds_by_order(
        self,
        order_reference: str,
    ) -> list[Refund]:

        result = await self.db.execute(
            select(Refund)
            .where(
                Refund.order_reference == order_reference
            )
            .order_by(Refund.created_at.desc())
        )

        return result.scalars().all()