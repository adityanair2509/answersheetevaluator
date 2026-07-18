"""
tests/conftest.py

Shared pytest fixtures for the entire test suite.
"""

from __future__ import annotations

import os
import warnings

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Suppress starlette's cosmetic deprecation about httpx vs httpx2
warnings.filterwarnings("ignore", category=DeprecationWarning, module="starlette")
warnings.filterwarnings("ignore", message=".*httpx.*", category=DeprecationWarning)

# Force test environment so .env.example isn't accidentally loaded
os.environ.setdefault("APP_ENV", "development")
os.environ.setdefault("ALLOWED_TEACHER_IDS", "teacher_test")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./data/test.db")


@pytest.fixture(scope="session")
def api_client() -> TestClient:
    """Synchronous TestClient for the FastAPI app (session-scoped)."""
    from apps.api.main import app

    return TestClient(app)


# ── Test DB setup ─────────────────────────────────────────────────────────────


@pytest.fixture(scope="session", autouse=True)
def setup_test_db() -> None:
    """
    Ensure the test SQLite DB has all tables before any tests run.
    Runs once per session. Uses the DATABASE_URL from the environment (test.db).
    Also enables WAL journal mode for SQLite to reduce write-lock contention.
    """
    import asyncio

    async def _setup() -> None:
        from db.session import create_all_tables, engine

        async with engine.connect() as conn:
            # Enable WAL mode — allows concurrent readers + one writer
            await conn.execute(__import__("sqlalchemy").text("PRAGMA journal_mode=WAL"))
            await conn.commit()

        await create_all_tables()

    asyncio.run(_setup())


# ── Integration test fixtures ─────────────────────────────────────────────────


@pytest.fixture(scope="session")
def teacher_headers() -> dict[str, str]:
    """Auth headers for a test teacher in the allowlist."""
    return {"X-Teacher-Id": "teacher_test"}


@pytest.fixture(scope="session")
def tiny_jpeg_bytes() -> bytes:
    """
    Minimal valid 1×1 white JPEG bytes.
    Built without Pillow so there are no extra test dependencies.
    This is a minimal JFIF/JPEG binary for a single white pixel.
    """
    # fmt: off
    return bytes([
        0xFF, 0xD8, 0xFF, 0xE0,  # SOI + APP0 marker
        0x00, 0x10,              # APP0 length = 16
        0x4A, 0x46, 0x49, 0x46, 0x00,  # "JFIF\0"
        0x01, 0x01,              # version 1.1
        0x00,                    # aspect ratio units = 0 (no units)
        0x00, 0x01,              # X density = 1
        0x00, 0x01,              # Y density = 1
        0x00, 0x00,              # thumbnail dimensions 0×0
        # SOF0 — start of frame (baseline DCT)
        0xFF, 0xC0,
        0x00, 0x0B,              # length = 11
        0x08,                    # precision = 8
        0x00, 0x01,              # height = 1
        0x00, 0x01,              # width  = 1
        0x01,                    # components = 1 (grayscale)
        0x01, 0x11, 0x00,        # component 1: Y, sampling 1×1, qtable 0
        # DHT — Huffman table (minimal DC table for Y)
        0xFF, 0xC4,
        0x00, 0x1F,              # length = 31
        0x00,                    # table class=0 (DC), dest=0
        0x00, 0x01, 0x05, 0x01, 0x01, 0x01, 0x01, 0x01,
        0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
        0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07,
        0x08, 0x09, 0x0A, 0x0B,
        # DQT — quantization table
        0xFF, 0xDB,
        0x00, 0x43,              # length = 67
        0x00,                    # table 0, 8-bit
        *([0x10] * 64),          # 64 values = 16 (uniform quality)
        # SOS — start of scan
        0xFF, 0xDA,
        0x00, 0x08,              # length = 8
        0x01,                    # 1 component
        0x01, 0x00,              # component 1, DC/AC table 0
        0x00, 0x3F, 0x00,        # Ss=0, Se=63, Ah/Al=0
        # Compressed image data for a single white pixel
        0xF8,
        # EOI
        0xFF, 0xD9,
    ])
    # fmt: on


@pytest_asyncio.fixture
async def async_db_session():
    """
    Function-scoped async DB session using an isolated in-memory SQLite database.
    Creates all tables before the test and drops them after.
    """
    import db.models  # noqa: F401 — register all models
    from db.base import Base

    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )

    async with session_factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()
