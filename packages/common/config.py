"""
packages/common/config.py

Centralised Pydantic Settings for the entire application.
All values are read from environment variables (or a .env file).
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application-wide settings loaded from environment / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        # Tell pydantic-settings to split list[str] fields on commas
        # (avoids JSON-parsing a plain "a,b,c" string which raises JSONDecodeError)
        env_list_delimiter=",",  # type: ignore[typeddict-unknown-key]
    )

    # ── App ──────────────────────────────────────────────────────────────────
    app_env: Literal["development", "production"] = "development"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # ── OCR ──────────────────────────────────────────────────────────────────
    ocr_provider: Literal["google_vision", "paddle_ocr", "trocr"] = "google_vision"
    google_application_credentials: str | None = Field(
        default=None, alias="GOOGLE_APPLICATION_CREDENTIALS"
    )
    # REST API key alternative to service-account JSON
    google_vision_api_key: str | None = Field(default=None, alias="GOOGLE_VISION_API_KEY")
    ocr_cache_dir: Path = Path("./data/ocr_cache")

    # ── LLM ──────────────────────────────────────────────────────────────────
    llm_model: str = "claude-sonnet-4-20250514"
    anthropic_api_key: str | None = None
    openai_api_key: str | None = None

    # ── Embeddings ───────────────────────────────────────────────────────────
    embedding_provider: Literal["openai", "local"] = "local"
    embedding_model: str = "all-MiniLM-L6-v2"

    # ── Database ─────────────────────────────────────────────────────────────
    database_url: str = "sqlite+aiosqlite:///./data/evaluator.db"

    # ── Vector Store ─────────────────────────────────────────────────────────
    chroma_persist_dir: Path = Path("./data/chroma")

    # ── File Paths ───────────────────────────────────────────────────────────
    upload_dir: Path = Path("./data/uploads")

    # ── Auth ─────────────────────────────────────────────────────────────────
    # Declared as a plain str so pydantic-settings reads it verbatim (no JSON
    # parsing). The `allowed_teacher_ids` property splits on commas at call time.
    allowed_teacher_ids_raw: str = Field(default="", alias="ALLOWED_TEACHER_IDS")

    @property
    def allowed_teacher_ids(self) -> list[str]:
        """Parsed list of allowed teacher IDs from the comma-separated env var."""
        return [tid.strip() for tid in self.allowed_teacher_ids_raw.split(",") if tid.strip()]

    # ── Budget Controls ───────────────────────────────────────────────────────
    daily_vision_api_budget: int = 500
    daily_llm_token_budget: int = 1_000_000

    # ── Confidence Thresholds ─────────────────────────────────────────────────
    confidence_auto_approve: float = 0.85
    confidence_mandatory_review: float = 0.65

    # ── Helpers ───────────────────────────────────────────────────────────────
    @property
    def is_development(self) -> bool:
        return self.app_env == "development"

    def ensure_dirs(self) -> None:
        """Create data directories if they don't exist."""
        for d in (self.ocr_cache_dir, self.chroma_persist_dir, self.upload_dir):
            d.mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached singleton Settings instance."""
    return Settings()
