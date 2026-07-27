import uuid
from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest

from app.tasks import invoice_tasks, po_tasks

pytestmark = pytest.mark.unit


class TestInvoiceTasks:
    @patch("app.tasks.invoice_tasks.AsyncSessionLocal")
    async def test_reconcile_pending_invoices_processes_all(self, mock_session_local):
        mock_session = AsyncMock()
        mock_session_local.return_value.__aenter__.return_value = mock_session

        fake_result = AsyncMock()
        fake_result.all.return_value = [(uuid.uuid4(),), (uuid.uuid4(),)]
        mock_session.execute.return_value = fake_result

        with patch("app.tasks.invoice_tasks.InvoiceService") as mock_service_cls:
            mock_service = AsyncMock()
            mock_service_cls.return_value = mock_service
            result = await invoice_tasks._reconcile_pending_invoices()

        assert result["processed"] == 2
        assert mock_service.match_against_grn.await_count == 2

    @patch("app.tasks.invoice_tasks.AsyncSessionLocal")
    async def test_reconcile_pending_invoices_continues_on_error(self, mock_session_local):
        mock_session = AsyncMock()
        mock_session_local.return_value.__aenter__.return_value = mock_session

        fake_result = AsyncMock()
        fake_result.all.return_value = [(uuid.uuid4(),), (uuid.uuid4(),)]
        mock_session.execute.return_value = fake_result

        with patch("app.tasks.invoice_tasks.InvoiceService") as mock_service_cls:
            mock_service = AsyncMock()
            mock_service.match_against_grn.side_effect = [Exception("boom"), None]
            mock_service_cls.return_value = mock_service
            result = await invoice_tasks._reconcile_pending_invoices()

        # one failed, loop should not crash; processed only counts successes
        assert result["processed"] == 1

    @patch("app.tasks.invoice_tasks.FinanceServiceClient")
    @patch("app.tasks.invoice_tasks.AsyncSessionLocal")
    async def test_retry_unsynced_ledger_entries(self, mock_session_local, mock_client_cls):
        mock_session = AsyncMock()
        mock_session_local.return_value.__aenter__.return_value = mock_session

        entry = AsyncMock()
        entry.vendor_id = uuid.uuid4()
        entry.entry_type.value = "credit"
        entry.source.value = "invoice"
        entry.reference_id = None
        entry.amount = Decimal("100.00")
        entry.description = "test"
        entry.id = uuid.uuid4()

        fake_result = AsyncMock()
        fake_result.scalars.return_value.all.return_value = [entry]
        mock_session.execute.return_value = fake_result

        mock_client = AsyncMock()
        mock_client.post_journal_entry.return_value = "FIN-999"
        mock_client_cls.return_value = mock_client

        result = await invoice_tasks._retry_unsynced_ledger_entries()

        assert result["synced"] == 1
        assert entry.finance_service_synced is True
        assert entry.finance_service_ref == "FIN-999"


class TestPOTasks:
    @patch("app.tasks.po_tasks.AsyncSessionLocal")
    async def test_send_po_approval_reminders_counts_pending(self, mock_session_local):
        mock_session = AsyncMock()
        mock_session_local.return_value.__aenter__.return_value = mock_session

        po = AsyncMock()
        po.po_number = "PO-TEST-1"
        po.created_at = "2026-07-01"

        fake_result = AsyncMock()
        fake_result.scalars.return_value.all.return_value = [po]
        mock_session.execute.return_value = fake_result

        result = await po_tasks._send_po_approval_reminders()
        assert result["reminders_sent"] == 1

    @patch("app.tasks.po_tasks.AsyncSessionLocal")
    async def test_send_po_delivery_reminders_counts_due_soon(self, mock_session_local):
        mock_session = AsyncMock()
        mock_session_local.return_value.__aenter__.return_value = mock_session

        po = AsyncMock()
        po.po_number = "PO-TEST-2"
        po.expected_delivery_date = date.today()

        fake_result = AsyncMock()
        fake_result.scalars.return_value.all.return_value = [po]
        mock_session.execute.return_value = fake_result

        result = await po_tasks._send_po_delivery_reminders()
        assert result["reminders_sent"] == 1
