"""
Settlement reconciliation service.

Workflow:
  1. `start_run` creates a ReconciliationRun and ingests raw settlement rows
     as GatewaySettlement records (status=IMPORTED).
  2. `run_matching` (invoked synchronously here, or asynchronously by the
     Celery task in app.tasks.reconciliation_tasks) matches each settlement
     against the Orders service's expected payment amount:
       - exact match within tolerance -> MATCHED, ledger entry posted
       - amount mismatch -> MISMATCHED, ReconciliationException raised
       - no matching order found -> UNMATCHED, ReconciliationException raised
  3. Matched settlements generate a journal entry moving funds from the
     "Payment Gateway Clearing" account to the bank account, net of fees.
"""

import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import write_audit_log
from app.core.config import get_settings
from app.models.audit import AuditAction
from app.models.reconciliation import (
    GatewaySettlement,
    ReconciliationException,
    ReconciliationRun,
    ReconciliationRunStatus,
    SettlementStatus,
)
from app.schemas.journal import JournalEntryCreate, JournalLineIn
from app.schemas.reconciliation import ReconciliationExceptionResolve, ReconciliationRunCreate
from app.services.journal_service import JournalService
from app.services.ledger_service import LedgerService
from app.services.order_client import OrderServiceClient

settings = get_settings()

CLEARING_ACCOUNT_CODE = "1200"  # Payment Gateway Clearing - Juspay
BANK_ACCOUNT_CODE = "1100"  # Bank - Kotak Current Account
FEE_EXPENSE_ACCOUNT_CODE = "5100"  # Payment Gateway Fees
RECON_GAIN_ACCOUNT_CODE = "4900"
RECON_LOSS_ACCOUNT_CODE = "5900"


class ReconciliationService:
    def __init__(self, db: AsyncSession, order_client: OrderServiceClient | None = None):
        self.db = db
        self.order_client = order_client or OrderServiceClient()
        self.ledger_service = LedgerService(db)
        self.journal_service = JournalService(db)

    async def start_run(self, payload: ReconciliationRunCreate, *, actor: str) -> ReconciliationRun:
        run = ReconciliationRun(
            provider=payload.provider,
            settlement_batch_id=payload.settlement_batch_id,
            status=ReconciliationRunStatus.PENDING,
            total_records=len(payload.records),
            triggered_by=payload.triggered_by,
        )
        self.db.add(run)
        await self.db.flush()

        for record in payload.records:
            settlement = GatewaySettlement(
                run_id=run.id,
                provider=payload.provider,
                provider_transaction_id=record.provider_transaction_id,
                order_reference=record.order_reference,
                settled_amount_minor=record.settled_amount_minor,
                settlement_date=record.settlement_date,
                fee_amount_minor=record.fee_amount_minor,
                raw_payload=record.raw_payload,
                status=SettlementStatus.IMPORTED,
            )
            self.db.add(settlement)

        await write_audit_log(
            self.db,
            action=AuditAction.SETTLEMENT_IMPORTED,
            actor=actor,
            entity_type="reconciliation_run",
            entity_id=str(run.id),
            metadata={"provider": payload.provider.value, "record_count": len(payload.records)},
        )
        await self.db.commit()
        await self.db.refresh(run)
        return run

    async def run_matching(
        self, run_id: uuid.UUID, *, actor: str = "system:reconciliation-worker"
    ) -> ReconciliationRun:
        """
        Executes the matching pass for a run. Designed to be idempotent-ish:
        settlements already MATCHED are skipped on re-run.
        """
        run = await self._get_run(run_id)
        run.status = ReconciliationRunStatus.RUNNING
        await self.db.flush()

        await write_audit_log(
            self.db,
            action=AuditAction.RECONCILIATION_RUN_STARTED,
            actor=actor,
            entity_type="reconciliation_run",
            entity_id=str(run.id),
        )

        stmt = select(GatewaySettlement).where(
            GatewaySettlement.run_id == run_id, GatewaySettlement.status == SettlementStatus.IMPORTED
        )
        result = await self.db.execute(stmt)
        settlements = list(result.scalars().all())

        matched_count = 0
        exception_count = 0

        try:
            for settlement in settlements:
                matched = await self._match_settlement(settlement, actor=actor)
                if matched:
                    matched_count += 1
                else:
                    exception_count += 1

            run.matched_records = matched_count
            run.exception_records = exception_count
            run.status = ReconciliationRunStatus.COMPLETED
        except Exception as exc:  # noqa: BLE001 - we want to persist failure state
            run.status = ReconciliationRunStatus.FAILED
            run.error_message = str(exc)
            await self.db.commit()
            raise

        await write_audit_log(
            self.db,
            action=AuditAction.RECONCILIATION_RUN_COMPLETED,
            actor=actor,
            entity_type="reconciliation_run",
            entity_id=str(run.id),
            metadata={"matched": matched_count, "exceptions": exception_count},
        )
        await self.db.commit()
        await self.db.refresh(run)
        return run

    async def _match_settlement(self, settlement: GatewaySettlement, *, actor: str) -> bool:
        if not settlement.order_reference:
            await self._raise_exception(
                settlement,
                reason="Settlement has no order reference",
                expected=None,
                actual=settlement.settled_amount_minor,
            )
            return False

        expectation = await self.order_client.get_expected_payment(settlement.order_reference)
        if expectation is None:
            await self._raise_exception(
                settlement,
                reason="No matching order found in Orders service",
                expected=None,
                actual=settlement.settled_amount_minor,
            )
            return False

        diff = abs(expectation.expected_amount_minor - settlement.settled_amount_minor)
        if diff > settings.RECONCILIATION_AMOUNT_TOLERANCE_PAISE:
            settlement.status = SettlementStatus.MISMATCHED
            await self._raise_exception(
                settlement,
                reason=f"Amount mismatch: expected {expectation.expected_amount_minor}, got {settlement.settled_amount_minor}",
                expected=expectation.expected_amount_minor,
                actual=settlement.settled_amount_minor,
            )
            return False

        settlement.status = SettlementStatus.MATCHED
        await self._post_settlement_journal_entry(settlement)
        await self.db.flush()
        return True

    async def _raise_exception(
        self, settlement: GatewaySettlement, *, reason: str, expected: int | None, actual: int | None
    ) -> None:
        if settlement.status == SettlementStatus.IMPORTED:
            settlement.status = SettlementStatus.UNMATCHED
        exc_row = ReconciliationException(
            settlement_id=settlement.id,
            reason=reason,
            expected_amount_minor=expected,
            actual_amount_minor=actual,
        )
        self.db.add(exc_row)
        await self.db.flush()

    async def _post_settlement_journal_entry(self, settlement: GatewaySettlement) -> None:
        """
        DR Bank (net of fees), DR Payment Gateway Fees (expense),
        CR Payment Gateway Clearing (full settled amount).
        """
        clearing = await self._account_by_code(CLEARING_ACCOUNT_CODE)
        bank = await self._account_by_code(BANK_ACCOUNT_CODE)
        fees = await self._account_by_code(FEE_EXPENSE_ACCOUNT_CODE)

        net_amount = settlement.settled_amount_minor - settlement.fee_amount_minor
        lines = [
            JournalLineIn(account_id=bank.id, debit_amount_minor=net_amount, credit_amount_minor=0),
        ]
        if settlement.fee_amount_minor > 0:
            lines.append(
                JournalLineIn(account_id=fees.id, debit_amount_minor=settlement.fee_amount_minor, credit_amount_minor=0)
            )
        lines.append(
            JournalLineIn(
                account_id=clearing.id, debit_amount_minor=0, credit_amount_minor=settlement.settled_amount_minor
            )
        )

        payload = JournalEntryCreate(
            entry_date=settlement.settlement_date,
            description=f"Settlement {settlement.provider_transaction_id} for order {settlement.order_reference}",
            source_type="settlement",
            source_reference=settlement.order_reference or settlement.provider_transaction_id,
            lines=lines,
        )
        await self.journal_service.create_and_post_entry(payload, actor="system:reconciliation-worker")

    async def _account_by_code(self, code: str):
        accounts = await self.ledger_service.list_accounts(active_only=False)
        for account in accounts:
            if account.code == code:
                return account
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, f"Required system account '{code}' is missing")

    async def _get_run(self, run_id: uuid.UUID) -> ReconciliationRun:
        run = await self.db.get(ReconciliationRun, run_id)
        if run is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Reconciliation run not found")
        return run

    async def get_run(self, run_id: uuid.UUID) -> ReconciliationRun:
        """Public read-only accessor for a reconciliation run (used by the API layer)."""
        return await self._get_run(run_id)

    async def list_exceptions(self, *, resolved: bool | None = None) -> list[ReconciliationException]:
        stmt = select(ReconciliationException)
        if resolved is not None:
            stmt = stmt.where(ReconciliationException.resolved == resolved)
        stmt = stmt.order_by(ReconciliationException.created_at.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def resolve_exception(
        self, exception_id: uuid.UUID, payload: ReconciliationExceptionResolve, *, actor: str
    ) -> ReconciliationException:
        exc_row = await self.db.get(ReconciliationException, exception_id)
        if exc_row is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Reconciliation exception not found")
        exc_row.resolved = True
        exc_row.resolved_by = actor
        exc_row.resolution_notes = payload.resolution_notes

        await write_audit_log(
            self.db,
            action=AuditAction.RECONCILIATION_EXCEPTION_RESOLVED,
            actor=actor,
            entity_type="reconciliation_exception",
            entity_id=str(exc_row.id),
            metadata={"notes": payload.resolution_notes},
        )
        await self.db.commit()
        await self.db.refresh(exc_row)
        return exc_row
