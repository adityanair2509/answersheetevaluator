"""
tests/unit/test_config.py

Unit tests for packages/common/config.py
"""
from __future__ import annotations

import os

import pytest


def test_settings_defaults() -> None:
    """Settings load with sensible defaults even without a .env file."""
    from packages.common.config import get_settings

    get_settings.cache_clear()
    os.environ["ALLOWED_TEACHER_IDS"] = "teacher_demo"
    os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./data/test.db"

    settings = get_settings()
    assert settings.app_env in ("development", "production")
    assert settings.confidence_auto_approve == pytest.approx(0.85)
    assert settings.confidence_mandatory_review == pytest.approx(0.65)
    assert settings.api_port == 8000


def test_teacher_id_parsing() -> None:
    """Comma-separated teacher IDs from env are parsed into a list."""
    from packages.common.config import get_settings

    get_settings.cache_clear()
    os.environ["ALLOWED_TEACHER_IDS"] = "teacher_ravi, teacher_priya , teacher_amit"

    settings = get_settings()
    ids = settings.allowed_teacher_ids  # property call
    assert "teacher_ravi" in ids
    assert "teacher_priya" in ids
    assert "teacher_amit" in ids
    assert len(ids) == 3


def test_is_development_flag() -> None:
    from packages.common.config import get_settings

    get_settings.cache_clear()
    os.environ["APP_ENV"] = "development"
    os.environ["ALLOWED_TEACHER_IDS"] = "teacher_test"
    assert get_settings().is_development is True

    get_settings.cache_clear()
    os.environ["APP_ENV"] = "production"
    assert get_settings().is_development is False

    # Restore for other tests
    os.environ["APP_ENV"] = "development"
    get_settings.cache_clear()

