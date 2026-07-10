"""
Exponential backoff calculation with optional jitter, configurable per
channel via the `retry_policies` table (falls back to Settings defaults).
"""
import random
from datetime import datetime, timedelta, timezone

from app.config import get_settings

settings = get_settings()


def compute_next_retry(
    attempt_count: int,
    base_backoff_seconds: int = None,
    max_backoff_seconds: int = None,
    jitter: bool = True,
) -> datetime:
    """
    attempt_count is the number of attempts ALREADY made (>=1 by the time
    we compute the next retry). Backoff = base * 2^(attempt_count - 1),
    capped at max_backoff_seconds, with up to +/-20% jitter to avoid
    thundering-herd retries.
    """
    base = base_backoff_seconds or settings.default_base_backoff_seconds
    cap = max_backoff_seconds or settings.default_max_backoff_seconds

    delay = min(base * (2 ** max(attempt_count - 1, 0)), cap)
    if jitter:
        jitter_range = delay * 0.2
        delay += random.uniform(-jitter_range, jitter_range)
        delay = max(delay, 1)

    return datetime.now(timezone.utc) + timedelta(seconds=delay)


def should_dead_letter(attempt_count: int, max_retries: int) -> bool:
    return attempt_count >= max_retries
