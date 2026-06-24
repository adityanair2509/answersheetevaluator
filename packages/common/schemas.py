"""
packages/common/schemas.py

Shared Pydantic v2 models used across API request/response bodies
and inter-package data transfer. These are NOT ORM models.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from packages.common.enums import (
    AnswerKeyStatus,
    ConfidenceBand,
    ExamStatus,
    JobStatus,
    ReviewStatus,
    SheetStatus,
)


# ── Base ──────────────────────────────────────────────────────────────────────


class APIBase(BaseModel):
    """Base for all API models — forbids extra fields, uses attribute access."""

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        str_strip_whitespace=True,
    )


# ── Health ────────────────────────────────────────────────────────────────────


class HealthResponse(APIBase):
    status: str = "ok"
    version: str = "0.1.0"
    environment: str


# ── Exams ─────────────────────────────────────────────────────────────────────


class QuestionIn(APIBase):
    """A single question within an exam, as supplied by the teacher."""

    question_number: int = Field(..., ge=1)
    question_text: str = Field(..., min_length=1)
    max_marks: float = Field(..., gt=0)
    # Optional structured rubric hints (free-form until Week 3)
    rubric_hints: str | None = None


class ExamCreate(APIBase):
    title: str = Field(..., min_length=1, max_length=200)
    course_code: str | None = Field(default=None, max_length=50)
    questions: list[QuestionIn] = Field(default_factory=list)


class ExamOut(APIBase):
    id: int
    title: str
    course_code: str | None
    status: ExamStatus
    created_at: datetime
    question_count: int = 0


# ── Answer Sheets ─────────────────────────────────────────────────────────────


class AnswerSheetOut(APIBase):
    id: int
    exam_id: int
    student_roll: str | None
    original_filename: str
    status: SheetStatus
    page_count: int
    created_at: datetime


# ── OCR / Extracted Answers ───────────────────────────────────────────────────


class BoundingBox(APIBase):
    """Pixel-space bounding box for an OCR region."""

    x: int
    y: int
    width: int
    height: int
    page: int = 1


class ExtractedAnswerOut(APIBase):
    id: int
    answer_sheet_id: int
    question_number: int
    raw_text: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    bounding_boxes: list[BoundingBox] = Field(default_factory=list)


# ── Processing Jobs ────────────────────────────────────────────────────────────


class ProcessingJobOut(APIBase):
    id: int
    answer_sheet_id: int
    status: JobStatus
    stage: str | None
    error_message: str | None
    retry_count: int
    created_at: datetime
    updated_at: datetime


# ── Evaluation Results ────────────────────────────────────────────────────────


class ConceptScore(APIBase):
    """Score for a single atomic concept within an answer."""

    concept: str
    present: bool
    partial_credit: float = Field(0.0, ge=0.0, le=1.0)
    evidence: str | None = None


class EvaluationResultOut(APIBase):
    id: int
    extracted_answer_id: int
    score: float
    max_score: float
    reasoning: str
    concept_scores: list[ConceptScore] = Field(default_factory=list)
    confidence: float = Field(..., ge=0.0, le=1.0)
    confidence_band: ConfidenceBand
    review_status: ReviewStatus
    answer_key_version: int
    created_at: datetime


# ── Review Queue ──────────────────────────────────────────────────────────────


class ReviewQueueItemOut(APIBase):
    id: int
    evaluation_result_id: int
    student_roll: str | None
    question_number: int
    score: float
    max_score: float
    confidence: float
    confidence_band: ConfidenceBand
    status: ReviewStatus
    created_at: datetime


class OverrideIn(APIBase):
    """Teacher override payload for a single evaluation result."""

    new_score: float = Field(..., ge=0.0)
    override_reason: str = Field(..., min_length=5)


# ── Generic Responses ─────────────────────────────────────────────────────────


class MessageResponse(APIBase):
    message: str
    detail: Any | None = None


class PaginatedResponse(APIBase):
    """Thin wrapper for paginated list endpoints."""

    items: list[Any]
    total: int
    page: int = 1
    page_size: int = 50
