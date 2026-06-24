"""
packages/common/enums.py

Centralised enumeration types shared across the entire application.
"""
from __future__ import annotations

from enum import StrEnum


# ── Processing Jobs ──────────────────────────────────────────────────────────


class JobStatus(StrEnum):
    """Status of a background processing job."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


# ── OCR / Sheets ─────────────────────────────────────────────────────────────


class SheetStatus(StrEnum):
    """Lifecycle status of an uploaded answer sheet."""

    UPLOADED = "uploaded"
    PREPROCESSING = "preprocessing"
    OCR_RUNNING = "ocr_running"
    OCR_DONE = "ocr_done"
    EVALUATING = "evaluating"
    EVALUATED = "evaluated"
    FAILED = "failed"


class OCRProvider(StrEnum):
    """Supported OCR backends."""

    GOOGLE_VISION = "google_vision"
    PADDLE_OCR = "paddle_ocr"
    TROCR = "trocr"


# ── Evaluation / Review ───────────────────────────────────────────────────────


class ReviewStatus(StrEnum):
    """Human-in-the-loop review status for an evaluation result."""

    PENDING = "pending"
    AUTO_APPROVED = "auto_approved"
    NEEDS_REVIEW = "needs_review"
    REVIEWED = "reviewed"
    OVERRIDDEN = "overridden"
    SKIPPED = "skipped"


class ConfidenceBand(StrEnum):
    """Categorical confidence level for UI colour-coding."""

    HIGH = "high"       # >= 0.85 → green, auto-approve
    MEDIUM = "medium"   # 0.65–0.85 → yellow, optional review
    LOW = "low"         # < 0.65 → red, mandatory review


# ── Answer Keys ───────────────────────────────────────────────────────────────


class AnswerKeyStatus(StrEnum):
    """Processing state of an uploaded answer key."""

    UPLOADED = "uploaded"
    DECOMPOSING = "decomposing"
    EMBEDDING = "embedding"
    READY = "ready"
    FAILED = "failed"


# ── Exams ─────────────────────────────────────────────────────────────────────


class ExamStatus(StrEnum):
    """Overall status of an exam from the teacher's perspective."""

    DRAFT = "draft"
    ACCEPTING_UPLOADS = "accepting_uploads"
    PROCESSING = "processing"
    GRADED = "graded"
    EXPORTED = "exported"
