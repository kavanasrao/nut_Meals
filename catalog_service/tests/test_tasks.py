"""Unit tests for Celery background tasks (moderation + redirect sync)."""
from unittest.mock import AsyncMock, patch

import pytest

from app.tasks.moderation_tasks import recompute_rating_aggregate_task
from app.tasks.redirect_tasks import cleanup_old_redirect_logs


def test_recompute_rating_aggregate_task_runs_and_commits():
    fake_session = AsyncMock()
    fake_session.__aenter__.return_value = fake_session
    fake_session.__aexit__.return_value = None

    with patch("app.tasks.moderation_tasks.AsyncSessionLocal", return_value=fake_session), patch(
        "app.services.review_service.recompute_rating_aggregate", new=AsyncMock()
    ) as mock_recompute:
        recompute_rating_aggregate_task.run("11111111-1111-1111-1111-111111111111")

    mock_recompute.assert_awaited_once()
    fake_session.commit.assert_awaited_once()


def test_recompute_rating_aggregate_task_retries_on_failure():
    with patch("app.tasks.moderation_tasks.AsyncSessionLocal", side_effect=RuntimeError("db down")):
        with pytest.raises(Exception):
            recompute_rating_aggregate_task.apply(
                args=["11111111-1111-1111-1111-111111111111"], throw=True
            )


def test_cleanup_old_redirect_logs_executes_delete():
    fake_session = AsyncMock()
    fake_session.__aenter__.return_value = fake_session
    fake_session.__aexit__.return_value = None
    fake_result = AsyncMock()
    fake_result.rowcount = 3
    fake_session.execute = AsyncMock(return_value=fake_result)

    with patch("app.tasks.redirect_tasks.AsyncSessionLocal", return_value=fake_session):
        cleanup_old_redirect_logs.run()

    fake_session.execute.assert_awaited_once()
    fake_session.commit.assert_awaited_once()
