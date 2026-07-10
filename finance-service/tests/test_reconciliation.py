from unittest.mock import AsyncMock

import pytest

from app.models.ledger import AccountType
from app.models.reconciliation import ReconciliationRunStatus
from app.schemas.ledger import LedgerAccountCreate
from app.schemas.reconciliation import ReconciliationExceptionResolve, ReconciliationRunCreate, SettlementRecordIn
from app.services.ledger_service import LedgerService
from app.services.order_client import OrderPaymentExpectation
from app.services.reconciliation_service import (
    BANK_ACCOUNT_CODE,
    CLEARING_ACCOUNT_CODE,
    FEE_EXPENSE_ACCOUNT_CODE,
    ReconciliationService,
)


async def _ensure_system_accounts(db_session):
    """Reconciliation posts to fixed account codes; ensure they exist for tests
    (in production these come from the seed migration)."""
    ledger = LedgerService(db_session)
    existing = {a.code for a in await ledger.list_accounts(active_only=False)}
    to_create = [
        (CLEARING_ACCOUNT_CODE, "Payment Gateway Clearing", AccountType.ASSET),
        (BANK_ACCOUNT_CODE, "Bank Account", AccountType.ASSET),
        (FEE_EXPENSE_ACCOUNT_CODE, "Gateway Fees", AccountType.EXPENSE),
    ]
    for code, name, acc_type in to_create:
        if code not in existing:
            await ledger.create_account(
                LedgerAccountCreate(code=code, name=name, account_type=acc_type), actor="tester"
            )


@pytest.mark.asyncio
async def test_matched_settlement_posts_journal_entry(db_session):
    await _ensure_system_accounts(db_session)
    mock_client = AsyncMock()
    mock_client.get_expected_payment.return_value = OrderPaymentExpectation(
        order_id="ORD-100", expected_amount_minor=10000, status="paid"
    )
    service = ReconciliationService(db_session, order_client=mock_client)

    run = await service.start_run(
        ReconciliationRunCreate(
            provider="juspay",
            settlement_batch_id="BATCH-1",
            records=[
                SettlementRecordIn(
                    provider_transaction_id="TXN-1",
                    order_reference="ORD-100",
                    settled_amount_minor=10000,
                    settlement_date="2026-07-10",
                    fee_amount_minor=200,
                )
            ],
        ),
        actor="tester",
    )
    completed = await service.run_matching(run.id, actor="tester")

    assert completed.status == ReconciliationRunStatus.COMPLETED
    assert completed.matched_records == 1
    assert completed.exception_records == 0


@pytest.mark.asyncio
async def test_mismatched_amount_flags_exception(db_session):
    await _ensure_system_accounts(db_session)
    mock_client = AsyncMock()
    mock_client.get_expected_payment.return_value = OrderPaymentExpectation(
        order_id="ORD-200", expected_amount_minor=20000, status="paid"
    )
    service = ReconciliationService(db_session, order_client=mock_client)

    run = await service.start_run(
        ReconciliationRunCreate(
            provider="juspay",
            settlement_batch_id="BATCH-2",
            records=[
                SettlementRecordIn(
                    provider_transaction_id="TXN-2",
                    order_reference="ORD-200",
                    settled_amount_minor=15000,  # mismatch vs expected 20000
                    settlement_date="2026-07-10",
                )
            ],
        ),
        actor="tester",
    )
    completed = await service.run_matching(run.id, actor="tester")

    assert completed.matched_records == 0
    assert completed.exception_records == 1

    exceptions = await service.list_exceptions(resolved=False)
    assert len(exceptions) == 1
    assert exceptions[0].expected_amount_minor == 20000
    assert exceptions[0].actual_amount_minor == 15000


@pytest.mark.asyncio
async def test_unmatched_settlement_when_order_not_found(db_session):
    await _ensure_system_accounts(db_session)
    mock_client = AsyncMock()
    mock_client.get_expected_payment.return_value = None
    service = ReconciliationService(db_session, order_client=mock_client)

    run = await service.start_run(
        ReconciliationRunCreate(
            provider="kotak_bank",
            settlement_batch_id="BATCH-3",
            records=[
                SettlementRecordIn(
                    provider_transaction_id="TXN-3",
                    order_reference="ORD-UNKNOWN",
                    settled_amount_minor=5000,
                    settlement_date="2026-07-10",
                )
            ],
        ),
        actor="tester",
    )
    completed = await service.run_matching(run.id, actor="tester")

    assert completed.exception_records == 1
    exceptions = await service.list_exceptions(resolved=False)
    assert "No matching order" in exceptions[0].reason


@pytest.mark.asyncio
async def test_resolve_exception_marks_resolved(db_session):
    await _ensure_system_accounts(db_session)
    mock_client = AsyncMock()
    mock_client.get_expected_payment.return_value = None
    service = ReconciliationService(db_session, order_client=mock_client)

    run = await service.start_run(
        ReconciliationRunCreate(
            provider="juspay",
            settlement_batch_id="BATCH-4",
            records=[
                SettlementRecordIn(
                    provider_transaction_id="TXN-4",
                    order_reference="ORD-XYZ",
                    settled_amount_minor=1000,
                    settlement_date="2026-07-10",
                )
            ],
        ),
        actor="tester",
    )
    await service.run_matching(run.id, actor="tester")
    exceptions = await service.list_exceptions(resolved=False)
    exception = exceptions[0]

    resolved = await service.resolve_exception(
        exception.id,
        ReconciliationExceptionResolve(resolution_notes="Manually verified with bank statement"),
        actor="tester",
    )
    assert resolved.resolved is True
    assert resolved.resolved_by == "tester"

    still_unresolved = await service.list_exceptions(resolved=False)
    assert exception.id not in [e.id for e in still_unresolved]


@pytest.mark.asyncio
async def test_amount_within_tolerance_still_matches(db_session):
    """Settlements within RECONCILIATION_AMOUNT_TOLERANCE_PAISE of expected should match, not mismatch."""
    await _ensure_system_accounts(db_session)
    mock_client = AsyncMock()
    mock_client.get_expected_payment.return_value = OrderPaymentExpectation(
        order_id="ORD-300", expected_amount_minor=10000, status="paid"
    )
    service = ReconciliationService(db_session, order_client=mock_client)

    run = await service.start_run(
        ReconciliationRunCreate(
            provider="juspay",
            settlement_batch_id="BATCH-5",
            records=[
                SettlementRecordIn(
                    provider_transaction_id="TXN-5",
                    order_reference="ORD-300",
                    settled_amount_minor=10050,  # within default 100 paise tolerance
                    settlement_date="2026-07-10",
                )
            ],
        ),
        actor="tester",
    )
    completed = await service.run_matching(run.id, actor="tester")
    assert completed.matched_records == 1
