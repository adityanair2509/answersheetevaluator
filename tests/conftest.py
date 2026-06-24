"""
tests/conftest.py

Shared pytest fixtures for the entire test suite.
Additional fixtures will be added in Day 6-7 (DB session, TestClient).
"""
from __future__ import annotations

import os
import warnings

import pytest
from fastapi.testclient import TestClient

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
