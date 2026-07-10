"""Unit tests for Celery background tasks (renewal billing + reminders).

These exercise the task functions directly (eager, no broker needed) with
httpx and the sync DB session mocked/patched.
"""
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from app.models.subscription import SubscriptionStatus


class FakeSubscription:
    def __init__(self, status=SubscriptionStatus.ACTIVE, failed_attempts=0, frequency_value="weekly"):
        self.id = "sub-1"
        self.status = status
        self.failed_renewal_attempts = failed_attempts
        self.payment_method_token = "pm_tok_1"
        self.price_amount = 50.0
        self.currency = "USD"
        self.next_renewal_date = datetime.now(timezone.utc) - timedelta(hours=1)
        self.last_renewed_at = None
        self.renewal_notice_sent = False

        class _Freq:
            value = frequency_value

        self.frequency = _Freq()


class TestProcessDueRenewals:
    @patch("app.tasks.subscription_tasks.Session")
    @patch("app.tasks.subscription_tasks.httpx.post")
    def test_successful_renewal_advances_next_date(self, mock_post, mock_session_cls):
        from app.tasks.subscription_tasks import process_due_renewals

        mock_post.return_value = MagicMock(status_code=200, raise_for_status=lambda: None)

        sub = FakeSubscription()
        mock_session = MagicMock()
        mock_session.execute.return_value.scalars.return_value.all.return_value = [sub]
        mock_session_cls.return_value.__enter__.return_value = mock_session

        result = process_due_renewals()

        assert result["succeeded"] == 1
        assert sub.failed_renewal_attempts == 0
        assert sub.status == SubscriptionStatus.ACTIVE
        mock_session.commit.assert_called_once()

    @patch("app.tasks.subscription_tasks.Session")
    @patch("app.tasks.subscription_tasks.httpx.post")
    def test_failed_renewal_increments_attempts(self, mock_post, mock_session_cls):
        from app.tasks.subscription_tasks import process_due_renewals
        import httpx

        mock_post.side_effect = httpx.HTTPError("payment declined")

        sub = FakeSubscription()
        mock_session = MagicMock()
        mock_session.execute.return_value.scalars.return_value.all.return_value = [sub]
        mock_session_cls.return_value.__enter__.return_value = mock_session

        result = process_due_renewals()

        assert result["failed"] == 1
        assert sub.failed_renewal_attempts == 1
        assert sub.status == SubscriptionStatus.ACTIVE  # not yet past_due

    @patch("app.tasks.subscription_tasks.Session")
    @patch("app.tasks.subscription_tasks.httpx.post")
    def test_marks_past_due_after_max_attempts(self, mock_post, mock_session_cls):
        from app.tasks.subscription_tasks import process_due_renewals
        import httpx

        mock_post.side_effect = httpx.HTTPError("payment declined")

        sub = FakeSubscription(failed_attempts=2)
        mock_session = MagicMock()
        mock_session.execute.return_value.scalars.return_value.all.return_value = [sub]
        mock_session_cls.return_value.__enter__.return_value = mock_session

        process_due_renewals()

        assert sub.failed_renewal_attempts == 3
        assert sub.status == SubscriptionStatus.PAST_DUE
