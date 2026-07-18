"""
apps/api/jobs.py

Lightweight in-process async OCR background job runner.

Design:
  - Uses asyncio.create_task() for fire-and-forget execution.
  - The synchronous OCR pipeline is offloaded to a thread via asyncio.to_thread().
  - All DB writes use a fresh AsyncSession (not the request session, which is already closed).
  - Job state transitions: pending → running → completed | failed

Usage (called from routers/sheets.py):
    asyncio.create_task(run_ocr_job(sheet_id=sheet.id, job_id=job.id))
"""

from __future__ import annotations

import asyncio
import traceback

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.common.enums import JobStatus, SheetStatus
from packages.common.logging import get_logger

logger = get_logger(__name__)


async def run_ocr_job(sheet_id: int, job_id: int) -> None:
    """
    Execute the full OCR pipeline for one answer sheet in the background.

    Stages:
        1. Transition job → running
        2. Load SheetPage file paths from DB
        3. Call run_ocr_pipeline() via asyncio.to_thread() (blocking → async)
        4. Upsert ExtractedAnswer rows for each SegmentedAnswer
        5. Store raw OCR JSON in SheetPage.ocr_raw_json
        6. Transition sheet → ocr_done, job → completed
        On any error: mark sheet → failed, job → failed with error_message.
    """
    from db.session import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        try:
            await _run(db, sheet_id, job_id)
        except Exception as exc:
            # Safety net: if _run itself fails before it can update the DB,
            # catch here and attempt a last-ditch failure mark.
            logger.exception(
                "ocr_job.unhandled_error", sheet_id=sheet_id, job_id=job_id, exc=str(exc)
            )
            try:
                await _mark_failed(db, job_id, sheet_id, traceback.format_exc())
            except Exception:
                logger.exception("ocr_job.failed_to_mark_failure", sheet_id=sheet_id, job_id=job_id)


async def _run(db: AsyncSession, sheet_id: int, job_id: int) -> None:
    """Inner implementation — expects a fresh session."""
    from db.models import AnswerSheet, ExtractedAnswer, ProcessingJob, SheetPage
    from packages.common.config import get_settings
    from packages.ocr.pipeline import run_ocr_pipeline

    settings = get_settings()

    # ── Step 1: transition job → running ─────────────────────────────────────
    job_result = await db.execute(select(ProcessingJob).where(ProcessingJob.id == job_id))
    job = job_result.scalar_one_or_none()
    if job is None:
        logger.error("ocr_job.job_not_found", job_id=job_id)
        return

    job.status = JobStatus.RUNNING
    job.stage = "preprocessing"
    await db.commit()

    logger.info("ocr_job.started", sheet_id=sheet_id, job_id=job_id)

    # ── Step 2: load sheet + pages ────────────────────────────────────────────
    sheet_result = await db.execute(select(AnswerSheet).where(AnswerSheet.id == sheet_id))
    sheet = sheet_result.scalar_one_or_none()
    if sheet is None:
        await _mark_failed(db, job_id, sheet_id, f"AnswerSheet {sheet_id} not found in DB.")
        return

    pages_result = await db.execute(
        select(SheetPage)
        .where(SheetPage.answer_sheet_id == sheet_id)
        .order_by(SheetPage.page_number)
    )
    pages = pages_result.scalars().all()

    if not pages:
        await _mark_failed(db, job_id, sheet_id, "No pages found for this sheet.")
        return

    # ── Step 3: select OCR client ─────────────────────────────────────────────
    # For now, always use the MockVisionClient so tests don't need credentials.
    # When real credentials are configured, swap in GoogleVisionRestClient / SDK client.
    ocr_client = _build_ocr_client(settings)

    # Load question numbers for this exam
    from sqlalchemy import select as sa_select

    from db.models import Question

    q_result = await db.execute(
        sa_select(Question.question_number).where(Question.exam_id == sheet.exam_id)
    )
    question_numbers = [row[0] for row in q_result.all()] or None

    # ── Step 4: run OCR for each page ─────────────────────────────────────────
    job.stage = "ocr_running"
    await db.commit()

    all_segmented = []
    for page in pages:
        logger.debug("ocr_job.page_start", page=page.page_number, path=page.file_path)

        # Run blocking OCR in a thread so we don't block the event loop
        try:
            segmented_answers = await asyncio.to_thread(
                run_ocr_pipeline,
                page.file_path,
                question_numbers,
                ocr_client,
                page.page_number,
            )
        except FileNotFoundError as exc:
            await _mark_failed(db, job_id, sheet_id, f"File not found: {exc}")
            return
        except Exception as exc:
            await _mark_failed(
                db, job_id, sheet_id, f"OCR failed on page {page.page_number}: {exc}"
            )
            return

        # Store raw OCR JSON on the page row
        # We can't easily get OCRResult here without refactoring pipeline —
        # store a lightweight summary instead.
        page.ocr_raw_json = {
            "page": page.page_number,
            "question_count": len(segmented_answers),
            "questions": [sa.question_number for sa in segmented_answers],
        }

        all_segmented.extend(segmented_answers)
        logger.debug(
            "ocr_job.page_done",
            page=page.page_number,
            answers_found=len(segmented_answers),
        )

    await db.commit()

    # ── Step 5: upsert ExtractedAnswer rows ───────────────────────────────────
    job.stage = "storing_answers"
    await db.commit()

    for seg in all_segmented:
        # Check if an ExtractedAnswer already exists for this sheet+question
        ea_result = await db.execute(
            select(ExtractedAnswer).where(
                ExtractedAnswer.answer_sheet_id == sheet_id,
                ExtractedAnswer.question_number == seg.question_number,
            )
        )
        existing_ea = ea_result.scalar_one_or_none()

        if existing_ea:
            existing_ea.raw_text = seg.raw_text
            existing_ea.confidence = seg.ocr_confidence
            existing_ea.bounding_boxes = seg.bounding_boxes
        else:
            db.add(
                ExtractedAnswer(
                    answer_sheet_id=sheet_id,
                    question_number=seg.question_number,
                    raw_text=seg.raw_text,
                    confidence=seg.ocr_confidence,
                    bounding_boxes=seg.bounding_boxes,
                )
            )

    # ── Step 6: finalise ──────────────────────────────────────────────────────
    sheet.status = SheetStatus.OCR_DONE
    job.status = JobStatus.COMPLETED
    job.stage = "done"
    await db.commit()

    logger.info(
        "ocr_job.completed",
        sheet_id=sheet_id,
        job_id=job_id,
        answers_stored=len(all_segmented),
    )


async def _mark_failed(
    db: AsyncSession,
    job_id: int,
    sheet_id: int,
    error_message: str,
) -> None:
    """Transition job and sheet to failed state."""
    from db.models import AnswerSheet, ProcessingJob

    try:
        job_result = await db.execute(select(ProcessingJob).where(ProcessingJob.id == job_id))
        job = job_result.scalar_one_or_none()
        if job:
            job.status = JobStatus.FAILED
            job.error_message = error_message[:2000]  # prevent DB overflow
            job.stage = "failed"

        sheet_result = await db.execute(select(AnswerSheet).where(AnswerSheet.id == sheet_id))
        sheet = sheet_result.scalar_one_or_none()
        if sheet:
            sheet.status = SheetStatus.FAILED

        await db.commit()
        logger.warning(
            "ocr_job.failed", sheet_id=sheet_id, job_id=job_id, error=error_message[:200]
        )
    except Exception as exc:
        logger.exception("ocr_job.failed_to_write_failure", exc=str(exc))


def _build_ocr_client(settings):  # type: ignore[no-untyped-def]
    """
    Select the appropriate OCR client based on available credentials.

    Priority:
        1. GoogleVisionRestClient  — if GOOGLE_VISION_API_KEY is set
        2. GoogleVisionSDKClient   — if GOOGLE_APPLICATION_CREDENTIALS is set
        3. MockVisionClient        — fallback (dev / CI)
    """
    from packages.ocr.vision_client import MockVisionClient

    if settings.google_vision_api_key:
        try:
            from packages.ocr.vision_client import GoogleVisionRestClient

            return GoogleVisionRestClient(api_key=settings.google_vision_api_key)
        except Exception:
            logger.warning("ocr_client.rest_init_failed, falling back to mock")

    if settings.google_application_credentials:
        try:
            from packages.ocr.vision_client import GoogleVisionSDKClient

            return GoogleVisionSDKClient()
        except Exception:
            logger.warning("ocr_client.sdk_init_failed, falling back to mock")

    return MockVisionClient()
