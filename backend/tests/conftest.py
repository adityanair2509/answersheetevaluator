"""
tests/conftest.py

Shared pytest fixtures for the entire test suite.
"""
from __future__ import annotations

import os
import asyncio
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
    from db.session import create_all_tables, AsyncSessionLocal
    from apps.api.main import app
    from db.models import Exam, Question
    import asyncio

    async def setup_db():
        await create_all_tables()
        async with AsyncSessionLocal() as session:
            # Seed a default exam and question for tests
            exam = Exam(title="Test Exam", course_code="TEST101")
            session.add(exam)
            await session.flush()

            question = Question(
                exam_id=exam.id,
                question_number=1,
                question_text="What is 2+2?",
                expected_answer="4",
                max_marks=10.0
            )
            session.add(question)
            await session.commit()

    asyncio.run(setup_db())

    with TestClient(app) as client:
        yield client
