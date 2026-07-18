"""
apps/api/routers/exams.py

Exam management routes:
    POST /api/v1/exams                          — Create exam + questions
    GET  /api/v1/exams                          — List all exams (paginated)
    GET  /api/v1/exams/{exam_id}                — Fetch exam details
    POST /api/v1/exams/{exam_id}/answer-key     — Upload / replace answer key text
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.dependencies import get_db, get_verified_teacher
from db.models import AnswerKey, Exam, Question
from packages.common.enums import AnswerKeyStatus
from packages.common.logging import get_logger
from packages.common.schemas import (
    AnswerKeyCreate,
    AnswerKeyOut,
    ExamCreate,
    ExamOut,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/exams", tags=["Exams"])


# ── POST /exams ───────────────────────────────────────────────────────────────


@router.post(
    "",
    response_model=ExamOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new exam with optional questions",
)
async def create_exam(
    payload: ExamCreate,
    db: AsyncSession = Depends(get_db),
    teacher_id: str = Depends(get_verified_teacher),
) -> ExamOut:
    """
    Create an exam and bulk-insert its questions in a single transaction.
    Returns the new exam with a question_count field.
    """
    exam = Exam(title=payload.title, course_code=payload.course_code)
    db.add(exam)
    await db.flush()  # get exam.id before inserting questions

    for q in payload.questions:
        db.add(
            Question(
                exam_id=exam.id,
                question_number=q.question_number,
                question_text=q.question_text,
                max_marks=q.max_marks,
                rubric_hints=q.rubric_hints,
            )
        )

    await db.commit()
    await db.refresh(exam)

    logger.info(
        "exam.created", exam_id=exam.id, teacher=teacher_id, questions=len(payload.questions)
    )

    return ExamOut(
        id=exam.id,
        title=exam.title,
        course_code=exam.course_code,
        status=exam.status,
        created_at=exam.created_at,
        question_count=len(payload.questions),
    )


# ── GET /exams ────────────────────────────────────────────────────────────────


@router.get(
    "",
    response_model=list[ExamOut],
    summary="List all exams",
)
async def list_exams(
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    teacher_id: str = Depends(get_verified_teacher),
) -> list[ExamOut]:
    """Return all exams with question counts, newest first."""
    result = await db.execute(
        select(Exam).order_by(Exam.created_at.desc()).offset(skip).limit(limit)
    )
    exams = result.scalars().all()

    # Build response with question counts via subquery
    out = []
    for exam in exams:
        count_result = await db.execute(
            select(func.count()).select_from(Question).where(Question.exam_id == exam.id)
        )
        q_count = count_result.scalar_one()
        out.append(
            ExamOut(
                id=exam.id,
                title=exam.title,
                course_code=exam.course_code,
                status=exam.status,
                created_at=exam.created_at,
                question_count=q_count,
            )
        )
    return out


# ── GET /exams/{exam_id} ──────────────────────────────────────────────────────


@router.get(
    "/{exam_id}",
    response_model=ExamOut,
    summary="Get exam details",
)
async def get_exam(
    exam_id: int,
    db: AsyncSession = Depends(get_db),
    teacher_id: str = Depends(get_verified_teacher),
) -> ExamOut:
    """Fetch a single exam by ID. Returns 404 if not found."""
    result = await db.execute(select(Exam).where(Exam.id == exam_id))
    exam = result.scalar_one_or_none()
    if exam is None:
        raise HTTPException(status_code=404, detail=f"Exam {exam_id} not found.")

    count_result = await db.execute(
        select(func.count()).select_from(Question).where(Question.exam_id == exam.id)
    )
    q_count = count_result.scalar_one()

    return ExamOut(
        id=exam.id,
        title=exam.title,
        course_code=exam.course_code,
        status=exam.status,
        created_at=exam.created_at,
        question_count=q_count,
    )


# ── POST /exams/{exam_id}/answer-key ─────────────────────────────────────────


@router.post(
    "/{exam_id}/answer-key",
    response_model=AnswerKeyOut,
    status_code=status.HTTP_201_CREATED,
    summary="Upload or replace the answer key for an exam (text body)",
)
async def upload_answer_key(
    exam_id: int,
    payload: AnswerKeyCreate,
    db: AsyncSession = Depends(get_db),
    teacher_id: str = Depends(get_verified_teacher),
) -> AnswerKeyOut:
    """
    Create or replace the answer key for an exam.
    At this stage (Day 6-7) only the raw text is stored and the status is set
    to `uploaded`.  RAG decomposition / embedding is a Week 2 concern.
    """
    # Verify exam exists
    exam_result = await db.execute(select(Exam).where(Exam.id == exam_id))
    exam = exam_result.scalar_one_or_none()
    if exam is None:
        raise HTTPException(status_code=404, detail=f"Exam {exam_id} not found.")

    # Check for an existing answer key
    ak_result = await db.execute(select(AnswerKey).where(AnswerKey.exam_id == exam_id))
    existing = ak_result.scalar_one_or_none()

    if existing:
        # Replace existing key: bump version and reset status
        existing.version = payload.version
        existing.status = AnswerKeyStatus.UPLOADED
        existing.file_path = None  # no file upload at this stage
        answer_key = existing
    else:
        answer_key = AnswerKey(
            exam_id=exam_id,
            status=AnswerKeyStatus.UPLOADED,
            version=payload.version,
        )
        db.add(answer_key)

    await db.commit()
    await db.refresh(answer_key)

    logger.info(
        "answer_key.uploaded",
        exam_id=exam_id,
        answer_key_id=answer_key.id,
        teacher=teacher_id,
    )

    return AnswerKeyOut(
        id=answer_key.id,
        exam_id=answer_key.exam_id,
        status=answer_key.status,
        version=answer_key.version,
        created_at=answer_key.created_at,
    )
