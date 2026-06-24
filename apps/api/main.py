"""
apps/api/main.py

FastAPI application entrypoint.

Usage:
    uv run uvicorn apps.api.main:app --reload --host 0.0.0.0 --port 8000
"""
from __future__ import annotations

import time
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from packages.common.config import get_settings
from packages.common.logging import configure_logging, get_logger
from packages.common.schemas import (
    AnswerSheetOut,
    EvaluationResultOut,
    ExamCreate,
    ExamOut,
    ExtractedAnswerOut,
    HealthResponse,
    MessageResponse,
    OverrideIn,
    ProcessingJobOut,
    ReviewQueueItemOut,
)
from packages.common.enums import (
    ConfidenceBand,
    ExamStatus,
    JobStatus,
    ReviewStatus,
    SheetStatus,
)

settings = get_settings()

# ── Logging ───────────────────────────────────────────────────────────────────
configure_logging(
    log_level=settings.log_level,
    as_json=not settings.is_development,
)
logger = get_logger(__name__)


# ── Lifespan ──────────────────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application startup and shutdown hooks."""
    # Ensure data directories exist
    settings.ensure_dirs()
    logger.info(
        "startup",
        env=settings.app_env,
        ocr_provider=settings.ocr_provider,
        llm_model=settings.llm_model,
    )
    yield
    logger.info("shutdown")


# ── App Factory ───────────────────────────────────────────────────────────────

app = FastAPI(
    title="Answer Sheet Evaluator API",
    description=(
        "Automated grading pipeline: OCR → RAG retrieval → LLM scoring → "
        "Human-in-the-loop review."
    ),
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
    # Fix: Swagger UI sends requests to the first server URL.
    # 0.0.0.0 is a bind address, NOT a valid browser target — use localhost.
    servers=[
        {"url": "http://localhost:8000", "description": "Local development server"},
    ],
)

# ── CORS ──────────────────────────────────────────────────────────────────────

# In development, allow the Next.js dev server origin.
# In production, replace with the actual deployed frontend URL.
_allowed_origins = (
    ["http://localhost:3000", "http://127.0.0.1:3000"]
    if settings.is_development
    else []  # set via environment in production
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request Timing Middleware ─────────────────────────────────────────────────


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):  # type: ignore[no-untyped-def]
    start = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = (time.perf_counter() - start) * 1000
    response.headers["X-Process-Time-Ms"] = f"{elapsed_ms:.1f}"
    logger.debug(
        "request",
        method=request.method,
        path=request.url.path,
        status=response.status_code,
        ms=round(elapsed_ms, 1),
    )
    return response


# ── Global Exception Handler ──────────────────────────────────────────────────


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("unhandled_error", path=request.url.path, exc=str(exc))
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected server error occurred."},
    )


# ── Core Routes ───────────────────────────────────────────────────────────────


@app.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    tags=["System"],
)
async def health() -> HealthResponse:
    """Returns 200 OK when the API is running."""
    return HealthResponse(environment=settings.app_env)


@app.get(
    "/api/v1/teachers",
    response_model=list[str],
    summary="List allowed teacher IDs",
    tags=["System"],
)
async def list_teachers() -> list[str]:
    """Returns the allowlist of teacher IDs (used by the frontend teacher selector)."""
    return settings.allowed_teacher_ids


# ── Routers (imported here as they are implemented) ───────────────────────────
# from apps.api.routers import sheets, exams   # uncomment in Day 6-7


# ── Schema Preview Routes (Dev Only) ─────────────────────────────────────────
# These routes serve as living documentation of every data model.
# They return example payloads so you can inspect the shapes in Swagger UI.
# All models in schemas.py are registered in the OpenAPI spec via these routes.


@app.get(
    "/api/v1/schema-preview/exam",
    response_model=ExamOut,
    summary="Example Exam response shape",
    tags=["Schema Preview"],
    include_in_schema=settings.is_development,
)
async def preview_exam() -> dict:
    """Returns an example ExamOut payload — for QA / docs inspection."""
    return {
        "id": 1,
        "title": "Mid-Term Computer Science 2024",
        "course_code": "CS301",
        "status": ExamStatus.ACCEPTING_UPLOADS,
        "created_at": "2024-11-01T09:00:00",
        "question_count": 5,
    }


@app.get(
    "/api/v1/schema-preview/answer-sheet",
    response_model=AnswerSheetOut,
    summary="Example AnswerSheet response shape",
    tags=["Schema Preview"],
    include_in_schema=settings.is_development,
)
async def preview_answer_sheet() -> dict:
    """Returns an example AnswerSheetOut payload."""
    return {
        "id": 42,
        "exam_id": 1,
        "student_roll": "2021CS001",
        "original_filename": "roll_2021CS001_sheet.jpg",
        "status": SheetStatus.OCR_DONE,
        "page_count": 2,
        "created_at": "2024-11-02T10:30:00",
    }


@app.get(
    "/api/v1/schema-preview/evaluation",
    response_model=EvaluationResultOut,
    summary="Example EvaluationResult response shape",
    tags=["Schema Preview"],
    include_in_schema=settings.is_development,
)
async def preview_evaluation() -> dict:
    """Returns an example EvaluationResultOut payload showing a scored answer."""
    return {
        "id": 7,
        "extracted_answer_id": 15,
        "score": 3.5,
        "max_score": 5.0,
        "reasoning": (
            "The student correctly identified the time complexity as O(n log n) "
            "and mentioned merge sort. However, they did not explain the space "
            "complexity trade-off."
        ),
        "concept_scores": [
            {"concept": "Correct time complexity O(n log n)", "present": True, "partial_credit": 1.0, "evidence": "Student wrote O(n log n)"},
            {"concept": "Names a divide-and-conquer algorithm", "present": True, "partial_credit": 1.0, "evidence": "Mentioned merge sort"},
            {"concept": "Explains space complexity", "present": False, "partial_credit": 0.0, "evidence": None},
        ],
        "confidence": 0.78,
        "confidence_band": ConfidenceBand.MEDIUM,
        "review_status": ReviewStatus.NEEDS_REVIEW,
        "answer_key_version": 1,
        "created_at": "2024-11-02T11:00:00",
    }


@app.get(
    "/api/v1/schema-preview/review-queue-item",
    response_model=ReviewQueueItemOut,
    summary="Example ReviewQueueItem response shape",
    tags=["Schema Preview"],
    include_in_schema=settings.is_development,
)
async def preview_review_queue_item() -> dict:
    """Returns an example ReviewQueueItemOut payload."""
    return {
        "id": 3,
        "evaluation_result_id": 7,
        "student_roll": "2021CS001",
        "question_number": 2,
        "score": 3.5,
        "max_score": 5.0,
        "confidence": 0.78,
        "confidence_band": ConfidenceBand.MEDIUM,
        "status": ReviewStatus.NEEDS_REVIEW,
        "created_at": "2024-11-02T11:00:00",
    }


@app.get(
    "/api/v1/schema-preview/processing-job",
    response_model=ProcessingJobOut,
    summary="Example ProcessingJob response shape",
    tags=["Schema Preview"],
    include_in_schema=settings.is_development,
)
async def preview_processing_job() -> dict:
    """Returns an example ProcessingJobOut payload."""
    return {
        "id": 9,
        "answer_sheet_id": 42,
        "status": JobStatus.RUNNING,
        "stage": "ocr_running",
        "error_message": None,
        "retry_count": 0,
        "created_at": "2024-11-02T10:30:01",
        "updated_at": "2024-11-02T10:30:05",
    }

