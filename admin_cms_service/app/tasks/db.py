"""
Celery workers use a synchronous SQLAlchemy session (separate engine from
the async one used by FastAPI request handlers) since Celery's execution
model is fundamentally synchronous. Async upstream-service HTTP calls
inside tasks are run via `asyncio.run(...)`.
"""
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings

settings = get_settings()

# Convert the async DSN (postgresql+asyncpg://) to a sync one (postgresql+psycopg://)
_sync_url = settings.database_url.replace("+asyncpg", "+psycopg")

sync_engine = create_engine(_sync_url, pool_pre_ping=True, future=True)
SyncSessionLocal = sessionmaker(bind=sync_engine, autoflush=False, expire_on_commit=False)


@contextmanager
def get_sync_db() -> Session:
    session = SyncSessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
