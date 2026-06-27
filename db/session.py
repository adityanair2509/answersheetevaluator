"""
db/session.py

Async SQLAlchemy engine, session factory, and FastAPI-compatible get_db() dependency.

Usage in FastAPI route:
    from db.session import get_db
    async def my_route(db: AsyncSession = Depends(get_db)):
        result = await db.execute(select(Exam))
"""
from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from packages.common.config import get_settings

# ---------------------------------------------------------------------------
# Engine — created once at module import time.
# Use connect_args for SQLite WAL mode (better concurrency under FastAPI).
# ---------------------------------------------------------------------------

_settings = get_settings()

_connect_args = (
    {"check_same_thread": False}
    if _settings.database_url.startswith("sqlite")
    else {}
)

engine = create_async_engine(
    _settings.database_url,
    echo=_settings.is_development,   # log SQL in dev, silent in prod
    future=True,
    connect_args=_connect_args,
)

# ---------------------------------------------------------------------------
# Session factory — expire_on_commit=False keeps objects usable after commit
# (important for returning ORM objects from async route handlers).
# ---------------------------------------------------------------------------

AsyncSessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------


async def get_db() -> AsyncIterator[AsyncSession]:
    """
    Yield an async database session scoped to a single request.

    The session is committed on success and rolled back + closed on any error.
    Inject with: ``db: AsyncSession = Depends(get_db)``
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ---------------------------------------------------------------------------
# Utility — used by seed script and tests
# ---------------------------------------------------------------------------


async def create_all_tables() -> None:
    """
    Create all tables defined in Base.metadata.

    Use only in dev/test contexts (not in production — use Alembic migrations).
    """
    from db.base import Base
    import db.models  # noqa: F401  — ensure all models are registered

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_all_tables() -> None:
    """
    Drop all tables — used in test teardown only.
    """
    from db.base import Base
    import db.models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
