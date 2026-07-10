from datetime import datetime, timezone

from app.core.retry_policy import compute_next_retry, should_dead_letter


def test_exponential_backoff_grows():
    t1 = compute_next_retry(attempt_count=1, base_backoff_seconds=10, max_backoff_seconds=10_000, jitter=False)
    t2 = compute_next_retry(attempt_count=2, base_backoff_seconds=10, max_backoff_seconds=10_000, jitter=False)
    t3 = compute_next_retry(attempt_count=3, base_backoff_seconds=10, max_backoff_seconds=10_000, jitter=False)

    now = datetime.now(timezone.utc)
    delay1 = (t1 - now).total_seconds()
    delay2 = (t2 - now).total_seconds()
    delay3 = (t3 - now).total_seconds()

    assert delay1 < delay2 < delay3


def test_backoff_respects_cap():
    t = compute_next_retry(attempt_count=20, base_backoff_seconds=10, max_backoff_seconds=60, jitter=False)
    now = datetime.now(timezone.utc)
    delay = (t - now).total_seconds()
    assert delay <= 61  # cap + tiny scheduling slack


def test_jitter_stays_within_reasonable_bounds():
    now = datetime.now(timezone.utc)
    t = compute_next_retry(attempt_count=3, base_backoff_seconds=100, max_backoff_seconds=10_000, jitter=True)
    delay = (t - now).total_seconds()
    # base delay for attempt 3 = 100 * 2^2 = 400, +-20% jitter => [320, 480]
    assert 300 <= delay <= 500


def test_should_dead_letter_true_when_exhausted():
    assert should_dead_letter(attempt_count=5, max_retries=5) is True
    assert should_dead_letter(attempt_count=6, max_retries=5) is True


def test_should_dead_letter_false_when_retries_remain():
    assert should_dead_letter(attempt_count=2, max_retries=5) is False
