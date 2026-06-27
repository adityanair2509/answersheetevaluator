"""
db/models.py

SQLAlchemy 2 ORM models — all 12 application tables.

Relationship diagram:
    exams ──── questions
      │
      ├── answer_keys ──── answer_key_chunks
      │
      └── answer_sheets ──── sheet_pages
                │
                └── extracted_answers ──── evaluation_results
                                                │
                                                ├── confidence_flags
                                                └── teacher_overrides

    processing_jobs  (linked to answer_sheets)
    audit_logs       (standalone, records all mutations)
    students         (optional — linked to answer_sheets)
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base, utcnow
from packages.common.enums import (
    AnswerKeyStatus,
    ConfidenceBand,
    ExamStatus,
    JobStatus,
    ReviewStatus,
    SheetStatus,
)


# ── 1. Students ───────────────────────────────────────────────────────────────


class Student(Base):
    """Optional student roster — linked to answer sheets for grade reporting."""

    __tablename__ = "students"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    roll_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=utcnow, nullable=False)

    # Relationships
    answer_sheets: Mapped[list[AnswerSheet]] = relationship(
        "AnswerSheet", back_populates="student"
    )

    def __repr__(self) -> str:
        return f"<Student roll={self.roll_number!r}>"


# ── 2. Exams ──────────────────────────────────────────────────────────────────


class Exam(Base):
    """A single examination — the root of the entire object graph."""

    __tablename__ = "exams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    course_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    status: Mapped[ExamStatus] = mapped_column(
        Enum(ExamStatus, name="exam_status"), default=ExamStatus.DRAFT, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(default=utcnow, nullable=False)

    # Relationships
    questions: Mapped[list[Question]] = relationship(
        "Question", back_populates="exam", cascade="all, delete-orphan"
    )
    answer_key: Mapped[AnswerKey | None] = relationship(
        "AnswerKey", back_populates="exam", uselist=False, cascade="all, delete-orphan"
    )
    answer_sheets: Mapped[list[AnswerSheet]] = relationship(
        "AnswerSheet", back_populates="exam", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Exam id={self.id} title={self.title!r}>"


# ── 3. Questions ──────────────────────────────────────────────────────────────


class Question(Base):
    """A single question within an exam (defined by the teacher when creating the exam)."""

    __tablename__ = "questions"
    __table_args__ = (
        UniqueConstraint("exam_id", "question_number", name="uq_exam_question_number"),
        Index("ix_questions_exam_id", "exam_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    exam_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("exams.id", ondelete="CASCADE"), nullable=False
    )
    question_number: Mapped[int] = mapped_column(Integer, nullable=False)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    max_marks: Mapped[float] = mapped_column(Float, nullable=False)
    rubric_hints: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    exam: Mapped[Exam] = relationship("Exam", back_populates="questions")

    def __repr__(self) -> str:
        return f"<Question exam_id={self.exam_id} q={self.question_number}>"


# ── 4. Answer Keys ────────────────────────────────────────────────────────────


class AnswerKey(Base):
    """
    Teacher-uploaded answer key for an exam.
    One exam has at most one answer key (enforced by unique FK).
    """

    __tablename__ = "answer_keys"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    exam_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("exams.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    status: Mapped[AnswerKeyStatus] = mapped_column(
        Enum(AnswerKeyStatus, name="answer_key_status"),
        default=AnswerKeyStatus.UPLOADED,
        nullable=False,
    )
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=utcnow, nullable=False)

    # Relationships
    exam: Mapped[Exam] = relationship("Exam", back_populates="answer_key")
    chunks: Mapped[list[AnswerKeyChunk]] = relationship(
        "AnswerKeyChunk", back_populates="answer_key", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<AnswerKey exam_id={self.exam_id} v={self.version}>"


# ── 5. Answer Key Chunks ──────────────────────────────────────────────────────


class AnswerKeyChunk(Base):
    """
    A single RAG chunk extracted from the answer key.
    Each chunk is vectorised and stored in ChromaDB; `chroma_id` links back.
    """

    __tablename__ = "answer_key_chunks"
    __table_args__ = (Index("ix_akc_answer_key_id", "answer_key_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    answer_key_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("answer_keys.id", ondelete="CASCADE"), nullable=False
    )
    question_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    chroma_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)

    # Relationships
    answer_key: Mapped[AnswerKey] = relationship("AnswerKey", back_populates="chunks")

    def __repr__(self) -> str:
        return f"<AnswerKeyChunk id={self.id} q={self.question_number}>"


# ── 6. Answer Sheets ──────────────────────────────────────────────────────────


class AnswerSheet(Base):
    """A student's uploaded answer sheet (one per student per exam)."""

    __tablename__ = "answer_sheets"
    __table_args__ = (Index("ix_answer_sheets_exam_id", "exam_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    exam_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("exams.id", ondelete="CASCADE"), nullable=False
    )
    student_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("students.id", ondelete="SET NULL"), nullable=True
    )
    student_roll: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    original_filename: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[SheetStatus] = mapped_column(
        Enum(SheetStatus, name="sheet_status"),
        default=SheetStatus.UPLOADED,
        nullable=False,
    )
    page_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=utcnow, nullable=False)

    # Relationships
    exam: Mapped[Exam] = relationship("Exam", back_populates="answer_sheets")
    student: Mapped[Student | None] = relationship("Student", back_populates="answer_sheets")
    pages: Mapped[list[SheetPage]] = relationship(
        "SheetPage", back_populates="answer_sheet", cascade="all, delete-orphan"
    )
    extracted_answers: Mapped[list[ExtractedAnswer]] = relationship(
        "ExtractedAnswer", back_populates="answer_sheet", cascade="all, delete-orphan"
    )
    processing_jobs: Mapped[list[ProcessingJob]] = relationship(
        "ProcessingJob", back_populates="answer_sheet", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<AnswerSheet id={self.id} roll={self.student_roll!r}>"


# ── 7. Sheet Pages ────────────────────────────────────────────────────────────


class SheetPage(Base):
    """
    A single page image from a multi-page answer sheet.
    `ocr_raw_json` stores the full raw Google Vision response for that page.
    """

    __tablename__ = "sheet_pages"
    __table_args__ = (Index("ix_sheet_pages_answer_sheet_id", "answer_sheet_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    answer_sheet_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("answer_sheets.id", ondelete="CASCADE"), nullable=False
    )
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    # Raw OCR JSON blob (Google Vision full response)
    ocr_raw_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    # Relationships
    answer_sheet: Mapped[AnswerSheet] = relationship("AnswerSheet", back_populates="pages")

    def __repr__(self) -> str:
        return f"<SheetPage sheet_id={self.answer_sheet_id} page={self.page_number}>"


# ── 8. Extracted Answers ──────────────────────────────────────────────────────


class ExtractedAnswer(Base):
    """
    OCR-extracted text for one question from one student's answer sheet.
    `bounding_boxes` stores a list of pixel-space regions (JSON array).
    """

    __tablename__ = "extracted_answers"
    __table_args__ = (Index("ix_extracted_answers_sheet_id", "answer_sheet_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    answer_sheet_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("answer_sheets.id", ondelete="CASCADE"), nullable=False
    )
    question_number: Mapped[int] = mapped_column(Integer, nullable=False)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    # List of BoundingBox dicts: [{x, y, width, height, page}, ...]
    bounding_boxes: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)

    # Relationships
    answer_sheet: Mapped[AnswerSheet] = relationship(
        "AnswerSheet", back_populates="extracted_answers"
    )
    evaluation_result: Mapped[EvaluationResult | None] = relationship(
        "EvaluationResult", back_populates="extracted_answer", uselist=False,
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<ExtractedAnswer sheet_id={self.answer_sheet_id} q={self.question_number}>"


# ── 9. Processing Jobs ────────────────────────────────────────────────────────


class ProcessingJob(Base):
    """
    Tracks the async grading pipeline for one answer sheet.
    One sheet can have multiple job attempts (retries tracked by retry_count).
    """

    __tablename__ = "processing_jobs"
    __table_args__ = (Index("ix_processing_jobs_sheet_id", "answer_sheet_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    answer_sheet_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("answer_sheets.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus, name="job_status"), default=JobStatus.PENDING, nullable=False
    )
    stage: Mapped[str | None] = mapped_column(String(100), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow, nullable=False)

    # Relationships
    answer_sheet: Mapped[AnswerSheet] = relationship(
        "AnswerSheet", back_populates="processing_jobs"
    )

    def __repr__(self) -> str:
        return f"<ProcessingJob id={self.id} status={self.status}>"


# ── 10. Evaluation Results ────────────────────────────────────────────────────


class EvaluationResult(Base):
    """
    LLM-produced score for one extracted answer.
    `concept_scores` is a JSON list of {concept, present, partial_credit, evidence} dicts.
    """

    __tablename__ = "evaluation_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    extracted_answer_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("extracted_answers.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    score: Mapped[float] = mapped_column(Float, nullable=False)
    max_score: Mapped[float] = mapped_column(Float, nullable=False)
    reasoning: Mapped[str] = mapped_column(Text, nullable=False, default="")
    # List of ConceptScore dicts
    concept_scores: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    confidence_band: Mapped[ConfidenceBand] = mapped_column(
        Enum(ConfidenceBand, name="confidence_band"),
        default=ConfidenceBand.LOW,
        nullable=False,
    )
    review_status: Mapped[ReviewStatus] = mapped_column(
        Enum(ReviewStatus, name="review_status"),
        default=ReviewStatus.PENDING,
        nullable=False,
    )
    answer_key_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=utcnow, nullable=False)

    # Relationships
    extracted_answer: Mapped[ExtractedAnswer] = relationship(
        "ExtractedAnswer", back_populates="evaluation_result"
    )
    confidence_flags: Mapped[list[ConfidenceFlag]] = relationship(
        "ConfidenceFlag", back_populates="evaluation_result", cascade="all, delete-orphan"
    )
    teacher_overrides: Mapped[list[TeacherOverride]] = relationship(
        "TeacherOverride", back_populates="evaluation_result", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<EvaluationResult id={self.id} score={self.score}/{self.max_score}>"


# ── 11. Confidence Flags ──────────────────────────────────────────────────────


class ConfidenceFlag(Base):
    """
    Machine-generated flags that explain WHY an evaluation was routed to review.
    Examples: 'low_ocr_confidence', 'retrieval_miss', 'score_boundary'.
    """

    __tablename__ = "confidence_flags"
    __table_args__ = (Index("ix_confidence_flags_eval_id", "evaluation_result_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    evaluation_result_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("evaluation_results.id", ondelete="CASCADE"), nullable=False
    )
    flag_type: Mapped[str] = mapped_column(String(100), nullable=False)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=utcnow, nullable=False)

    # Relationships
    evaluation_result: Mapped[EvaluationResult] = relationship(
        "EvaluationResult", back_populates="confidence_flags"
    )

    def __repr__(self) -> str:
        return f"<ConfidenceFlag type={self.flag_type!r}>"


# ── 12. Teacher Overrides ─────────────────────────────────────────────────────


class TeacherOverride(Base):
    """
    Human correction record — created when a teacher changes an LLM score.
    Acts as the primary audit trail for all human-in-the-loop interventions.
    """

    __tablename__ = "teacher_overrides"
    __table_args__ = (Index("ix_teacher_overrides_eval_id", "evaluation_result_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    evaluation_result_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("evaluation_results.id", ondelete="CASCADE"), nullable=False
    )
    teacher_id: Mapped[str] = mapped_column(String(100), nullable=False)
    old_score: Mapped[float] = mapped_column(Float, nullable=False)
    new_score: Mapped[float] = mapped_column(Float, nullable=False)
    override_reason: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=utcnow, nullable=False)

    # Relationships
    evaluation_result: Mapped[EvaluationResult] = relationship(
        "EvaluationResult", back_populates="teacher_overrides"
    )

    def __repr__(self) -> str:
        return (
            f"<TeacherOverride teacher={self.teacher_id!r} "
            f"{self.old_score}→{self.new_score}>"
        )
