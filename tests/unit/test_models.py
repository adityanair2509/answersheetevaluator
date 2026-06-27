"""
tests/unit/test_models.py

Unit tests for the SQLAlchemy ORM layer.
These tests only verify imports, metadata, and FK structure — no DB connection needed.
"""
from __future__ import annotations


# ── Test 1: All model classes importable ─────────────────────────────────────


def test_orm_imports() -> None:
    """All 12 ORM model classes must import without error."""
    from db.models import (  # noqa: F401
        AnswerKey,
        AnswerKeyChunk,
        AnswerSheet,
        ConfidenceFlag,
        EvaluationResult,
        Exam,
        ExtractedAnswer,
        ProcessingJob,
        Question,
        SheetPage,
        Student,
        TeacherOverride,
    )

    # Verify they are all distinct classes (not accidentally the same object)
    classes = [
        AnswerKey, AnswerKeyChunk, AnswerSheet, ConfidenceFlag,
        EvaluationResult, Exam, ExtractedAnswer, ProcessingJob,
        Question, SheetPage, Student, TeacherOverride,
    ]
    assert len(set(classes)) == 12, "Expected 12 distinct ORM model classes"


# ── Test 2: Metadata has exactly 12 tables ────────────────────────────────────


def test_table_count() -> None:
    """Base.metadata must contain exactly 12 registered tables."""
    from db.base import Base
    import db.models  # noqa: F401 — triggers model registration

    tables = set(Base.metadata.tables.keys())
    expected = {
        "students",
        "exams",
        "questions",
        "answer_keys",
        "answer_key_chunks",
        "answer_sheets",
        "sheet_pages",
        "extracted_answers",
        "processing_jobs",
        "evaluation_results",
        "confidence_flags",
        "teacher_overrides",
    }
    assert tables == expected, (
        f"Table mismatch.\nExpected: {sorted(expected)}\nGot:      {sorted(tables)}"
    )


# ── Test 3: Foreign key spot-checks ───────────────────────────────────────────


def test_foreign_keys() -> None:
    """Critical FK relationships must be correctly wired in the metadata."""
    from db.base import Base
    import db.models  # noqa: F401

    meta = Base.metadata

    # questions.exam_id → exams.id
    questions_table = meta.tables["questions"]
    fk_targets = {fk.column.table.name for fk in questions_table.foreign_keys}
    assert "exams" in fk_targets, "questions must have FK to exams"

    # answer_sheets.exam_id → exams.id
    sheets_table = meta.tables["answer_sheets"]
    fk_targets = {fk.column.table.name for fk in sheets_table.foreign_keys}
    assert "exams" in fk_targets, "answer_sheets must have FK to exams"

    # evaluation_results.extracted_answer_id → extracted_answers.id
    eval_table = meta.tables["evaluation_results"]
    fk_targets = {fk.column.table.name for fk in eval_table.foreign_keys}
    assert "extracted_answers" in fk_targets, (
        "evaluation_results must have FK to extracted_answers"
    )

    # teacher_overrides.evaluation_result_id → evaluation_results.id
    overrides_table = meta.tables["teacher_overrides"]
    fk_targets = {fk.column.table.name for fk in overrides_table.foreign_keys}
    assert "evaluation_results" in fk_targets, (
        "teacher_overrides must have FK to evaluation_results"
    )
