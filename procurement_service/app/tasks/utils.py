"""
Celery workers run tasks synchronously, but our services are async
(SQLAlchemy AsyncSession). This helper runs a coroutine to completion on a
fresh event loop, opening/closing its own DB session — Celery tasks must
never share a session across task invocations.
"""
import asyncio
from typing import Awaitable, Callable, TypeVar

T = TypeVar("T")


def run_async(coro_factory: Callable[[], Awaitable[T]]) -> T:
    """
    coro_factory is a zero-arg callable returning a coroutine, so a fresh
    coroutine/session is created per call (coroutines can't be reused).
    """
    return asyncio.run(coro_factory())
