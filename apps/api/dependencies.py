"""
apps/api/dependencies.py

FastAPI dependency injection providers.

Usage in route handlers::

    @router.post("/...")
    async def my_route(
        db: AsyncSession = Depends(get_db),
        teacher_id: str = Depends(get_verified_teacher),
    ):
        ...
"""
from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from packages.common.config import Settings, get_settings

# ---------------------------------------------------------------------------
# Database session — wired in Day 3 via db.session
# ---------------------------------------------------------------------------


async def get_db() -> AsyncIterator[AsyncSession]:
    """
    Yield an async SQLAlchemy session scoped to a single request.

    The session is committed on success and rolled back on any unhandled error.
    Delegates to db.session.get_db() so engine config lives in one place.
    """
    from db.session import get_db as _session_get_db

    async for session in _session_get_db():
        yield session


# ---------------------------------------------------------------------------
# Teacher auth (header-based allowlist)
# ---------------------------------------------------------------------------


def get_verified_teacher(
    x_teacher_id: str = Header(..., description="Teacher ID from the frontend allowlist"),
    settings: Settings = Depends(get_settings),
) -> str:
    """
    Validate that the requesting teacher is in the configured allowlist.

    Raises:
        HTTPException 403: if the teacher ID is not in ALLOWED_TEACHER_IDS.
    """
    if settings.allowed_teacher_ids and x_teacher_id not in settings.allowed_teacher_ids:
        raise HTTPException(
            status_code=403,
            detail=f"Teacher '{x_teacher_id}' is not authorised. "
            "Check ALLOWED_TEACHER_IDS in your .env file.",
        )
    return x_teacher_id
