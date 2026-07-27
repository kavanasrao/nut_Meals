"""Async SQLAlchemy engine + session factory."""
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

# SQLite (used in tests) does not support pool_size / max_overflow
_is_sqlite = settings.DATABASE_URL.startswith("sqlite")

_engine_kwargs: dict = {"echo": settings.DEBUG, "future": True}
if not _is_sqlite:
    _engine_kwargs["pool_size"] = settings.DB_POOL_SIZE
    _engine_kwargs["max_overflow"] = settings.DB_MAX_OVERFLOW

engine = create_async_engine(settings.DATABASE_URL, **_engine_kwargs)

AsyncSessionFactory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncSession:
    """FastAPI dependency — yields an async DB session."""
    async with AsyncSessionFactory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
