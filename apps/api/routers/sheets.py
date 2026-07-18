"""
apps/api/routers/sheets.py

Answer sheet routes:
    POST /api/v1/answer-sheets                          — Upload image file
    GET  /api/v1/answer-sheets/{sheet_id}               — Get sheet status + page list
    GET  /api/v1/answer-sheets/{sheet_id}/answers       — Get extracted answers
    POST /api/v1/answer-sheets/{sheet_id}/process       — Enqueue / re-enqueue OCR job
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.dependencies import get_db, get_verified_teacher
from apps.api.jobs import run_ocr_job
from db.models import AnswerSheet, Exam, ExtractedAnswer, ProcessingJob, SheetPage
from packages.common.enums import JobStatus, SheetStatus
from packages.common.logging import get_logger
from packages.common.schemas import (
    ExtractedAnswerOut,
    ProcessResponse,
    SheetDetailOut,
    SheetPageOut,
    SheetUploadResponse,
)


def _fire_background(coro) -> None:  # type: ignore[no-untyped-def]
    """
    Schedule a coroutine as a background task if an event loop is running.
    In synchronous test environments (e.g. Starlette TestClient with anyio)
    the task will be created on the running loop.
    If no loop is available, the coroutine is closed safely.
    """
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.ensure_future(coro)
        else:
            coro.close()
    except RuntimeError:
        coro.close()


logger = get_logger(__name__)

router = APIRouter(prefix="/answer-sheets", tags=["Sheets"])


# ── POST /answer-sheets ───────────────────────────────────────────────────────


@router.post(
    "",
    response_model=SheetUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload an answer sheet image and enqueue OCR",
)
async def upload_sheet(
    exam_id: int = Form(..., description="ID of the exam this sheet belongs to"),
    student_roll: str | None = Form(default=None, description="Student roll number (optional)"),
    file: UploadFile = File(..., description="Answer sheet image file"),
    db: AsyncSession = Depends(get_db),
    teacher_id: str = Depends(get_verified_teacher),
) -> SheetUploadResponse:
    """
    Upload a single answer-sheet image (JPEG / PNG).

    - Saves the file to `data/uploads/{exam_id}/{sheet_id}/page_1.{ext}`
    - Creates an `AnswerSheet` row + a `SheetPage` row
    - Creates a `ProcessingJob` row with status `pending`
    - Immediately enqueues an async background OCR task
    """
    from packages.common.config import get_settings

    # Verify exam exists
    exam_result = await db.execute(select(Exam).where(Exam.id == exam_id))
    exam = exam_result.scalar_one_or_none()
    if exam is None:
        raise HTTPException(status_code=404, detail=f"Exam {exam_id} not found.")

    original_filename = file.filename or "upload.jpg"
    ext = Path(original_filename).suffix.lower() or ".jpg"

    # Create AnswerSheet row first (need the id for the file path)
    sheet = AnswerSheet(
        exam_id=exam_id,
        student_roll=student_roll,
        original_filename=original_filename,
        status=SheetStatus.UPLOADED,
        page_count=1,
    )
    db.add(sheet)
    await db.flush()  # populate sheet.id

    # Determine upload path: data/uploads/{exam_id}/{sheet_id}/page_1{ext}
    settings = get_settings()
    upload_dir = settings.upload_dir / str(exam_id) / str(sheet.id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = upload_dir / f"page_1{ext}"

    # Write file to disk
    content = await file.read()
    file_path.write_bytes(content)

    # Create SheetPage row
    page = SheetPage(
        answer_sheet_id=sheet.id,
        page_number=1,
        file_path=str(file_path),
    )
    db.add(page)

    # Create ProcessingJob row
    job = ProcessingJob(
        answer_sheet_id=sheet.id,
        status=JobStatus.PENDING,
        stage="queued",
    )
    db.add(job)
    await db.flush()  # populate job.id

    await db.commit()

    logger.info(
        "sheet.uploaded",
        sheet_id=sheet.id,
        job_id=job.id,
        exam_id=exam_id,
        teacher=teacher_id,
        file=str(file_path),
    )

    # Fire-and-forget background task
    _fire_background(run_ocr_job(sheet_id=sheet.id, job_id=job.id))

    return SheetUploadResponse(
        answer_sheet_id=sheet.id,
        job_id=job.id,
        status=JobStatus.PENDING,
    )


# ── GET /answer-sheets/{sheet_id} ────────────────────────────────────────────


@router.get(
    "/{sheet_id}",
    response_model=SheetDetailOut,
    summary="Get sheet processing status and page list",
)
async def get_sheet(
    sheet_id: int,
    db: AsyncSession = Depends(get_db),
    teacher_id: str = Depends(get_verified_teacher),
) -> SheetDetailOut:
    """Return the sheet record, its pages, and the latest job status."""
    result = await db.execute(select(AnswerSheet).where(AnswerSheet.id == sheet_id))
    sheet = result.scalar_one_or_none()
    if sheet is None:
        raise HTTPException(status_code=404, detail=f"AnswerSheet {sheet_id} not found.")

    # Pages
    pages_result = await db.execute(
        select(SheetPage)
        .where(SheetPage.answer_sheet_id == sheet_id)
        .order_by(SheetPage.page_number)
    )
    pages = pages_result.scalars().all()

    # Latest job
    job_result = await db.execute(
        select(ProcessingJob)
        .where(ProcessingJob.answer_sheet_id == sheet_id)
        .order_by(ProcessingJob.id.desc())
        .limit(1)
    )
    latest_job = job_result.scalar_one_or_none()

    # Extracted answer count
    ea_result = await db.execute(
        select(ExtractedAnswer).where(ExtractedAnswer.answer_sheet_id == sheet_id)
    )
    ea_list = ea_result.scalars().all()

    return SheetDetailOut(
        id=sheet.id,
        exam_id=sheet.exam_id,
        student_roll=sheet.student_roll,
        original_filename=sheet.original_filename,
        status=sheet.status,
        page_count=sheet.page_count,
        created_at=sheet.created_at,
        pages=[
            SheetPageOut(id=p.id, page_number=p.page_number, file_path=p.file_path) for p in pages
        ],
        job_status=latest_job.status if latest_job else None,
        extracted_answer_count=len(ea_list),
    )


# ── GET /answer-sheets/{sheet_id}/answers ────────────────────────────────────


@router.get(
    "/{sheet_id}/answers",
    response_model=list[ExtractedAnswerOut],
    summary="Get extracted answers for a sheet",
)
async def get_answers(
    sheet_id: int,
    db: AsyncSession = Depends(get_db),
    teacher_id: str = Depends(get_verified_teacher),
) -> list[ExtractedAnswerOut]:
    """Return all OCR-extracted answers for a sheet, ordered by question number."""
    # Verify sheet exists
    sheet_result = await db.execute(select(AnswerSheet).where(AnswerSheet.id == sheet_id))
    if sheet_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail=f"AnswerSheet {sheet_id} not found.")

    result = await db.execute(
        select(ExtractedAnswer)
        .where(ExtractedAnswer.answer_sheet_id == sheet_id)
        .order_by(ExtractedAnswer.question_number)
    )
    answers = result.scalars().all()

    return [
        ExtractedAnswerOut(
            id=a.id,
            answer_sheet_id=a.answer_sheet_id,
            question_number=a.question_number,
            raw_text=a.raw_text,
            confidence=a.confidence,
            bounding_boxes=a.bounding_boxes or [],
        )
        for a in answers
    ]


# ── POST /answer-sheets/{sheet_id}/process ───────────────────────────────────


@router.post(
    "/{sheet_id}/process",
    response_model=ProcessResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Enqueue or re-enqueue the OCR processing job for a sheet",
)
async def process_sheet(
    sheet_id: int,
    db: AsyncSession = Depends(get_db),
    teacher_id: str = Depends(get_verified_teacher),
) -> ProcessResponse:
    """
    Manually enqueue the OCR pipeline for an existing sheet.
    If the sheet already has a running job, returns the current job status.
    Otherwise creates a new `ProcessingJob` and fires the background task.
    """
    sheet_result = await db.execute(select(AnswerSheet).where(AnswerSheet.id == sheet_id))
    sheet = sheet_result.scalar_one_or_none()
    if sheet is None:
        raise HTTPException(status_code=404, detail=f"AnswerSheet {sheet_id} not found.")

    # Check for an already-running job
    running_result = await db.execute(
        select(ProcessingJob).where(
            ProcessingJob.answer_sheet_id == sheet_id,
            ProcessingJob.status == JobStatus.RUNNING,
        )
    )
    running_job = running_result.scalar_one_or_none()
    if running_job:
        return ProcessResponse(
            job_id=running_job.id,
            status=running_job.status,
            message="A job is already running for this sheet.",
        )

    # Create new job
    job = ProcessingJob(
        answer_sheet_id=sheet_id,
        status=JobStatus.PENDING,
        stage="queued",
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    logger.info("sheet.process_enqueued", sheet_id=sheet_id, job_id=job.id, teacher=teacher_id)

    _fire_background(run_ocr_job(sheet_id=sheet_id, job_id=job.id))

    return ProcessResponse(
        job_id=job.id,
        status=JobStatus.PENDING,
        message="OCR job enqueued.",
    )
