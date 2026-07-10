"""Helper for running async DB operations from within synchronous Celery tasks."""
import asyncio
from typing import Awaitable, Callable, TypeVar

T = TypeVar("T")


def run_async(coro_fn: Callable[[], Awaitable[T]]) -> T:
    """Run an async coroutine to completion from sync Celery task code.

    Each call gets its own event loop since Celery worker threads/processes
    don't maintain a persistent asyncio loop between tasks.
    """
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro_fn())
    finally:
        loop.close()
