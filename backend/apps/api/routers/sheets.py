from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from typing import List, Optional
from pathlib import Path
import asyncio
from pydantic import BaseModel, Field

from db.session import get_db, AsyncSessionLocal
from db.models import AnswerSheet, ConfidenceFlag, EvaluationResult, Exam, ExtractedAnswer, Question, SheetPage, TeacherOverride, ProcessingJob
from packages.common.enums import SheetStatus, ReviewStatus, ConfidenceBand, JobStatus
from packages.common.config import get_settings
settings = get_settings()
from packages.ocr.gemini_evaluator import evaluate_answer_sheet
from packages.rag.chroma_service import chroma_service

async def process_answer_sheet_task(sheet_id: int, exam_id: int):
    """
    Background task to evaluate an answer sheet.
    Handles OCR, LLM evaluation, and DB persistence.
    """
    async with AsyncSessionLocal() as db:
        try:
            # 1. Create/Update Processing Job
            job = ProcessingJob(
                answer_sheet_id=sheet_id,
                status=JobStatus.RUNNING,
                stage="evaluating"
            )
            db.add(job)
            await db.flush()
            job_id = job.id

            # 2. Prepare files_data for evaluator
            # Retrieve all pages for this sheet
            page_query = select(SheetPage).where(SheetPage.answer_sheet_id == sheet_id).order_by(SheetPage.page_number)
            page_result = await db.execute(page_query)
            pages = page_result.scalars().all()

            files_data = []
            for p in pages:
                if p.file_path:
                    file_path = Path(p.file_path)
                    if file_path.exists():
                        # Determine mime type based on extension
                        ext = file_path.suffix.lower()
                        mime = "application/pdf" if ext == ".pdf" else "image/jpeg" if ext in [".jpg", ".jpeg"] else "image/png" if ext == ".png" else "application/octet-stream"
                        files_data.append({"bytes": file_path.read_bytes(), "mime_type": mime})

            if not files_data:
                raise ValueError("No valid files found for this answer sheet.")

            # 3. Evaluate against ALL questions in the exam
            q_query = select(Question).where(Question.exam_id == exam_id).order_by(Question.question_number)
            q_result = await db.execute(q_query)
            questions = q_result.scalars().all()

            for q in questions:
                # Retrieve RAG context
                reference_context = chroma_service.retrieve_context(exam_id, q.question_text) if q.question_text else None

                # Run synchronous AI evaluation in a separate thread to avoid blocking event loop
                evaluation = await asyncio.to_thread(
                    evaluate_answer_sheet,
                    files_data=files_data,
                    question_text=q.question_text,
                    expected_answer=q.expected_answer,
                    max_marks=q.max_marks,
                    reference_context=reference_context
                )

                # Persist ExtractedAnswer
                ai_conf = evaluation.get("aiConfidence", 78)
                conf_float = float(ai_conf) / 100.0 if ai_conf > 1 else float(ai_conf)

                extracted = ExtractedAnswer(
                    answer_sheet_id=sheet_id,
                    question_number=q.question_number,
                    raw_text=evaluation.get("studentAnswer", ""),
                    confidence=conf_float
                )
                db.add(extracted)
                await db.flush()

                # Persist EvaluationResult
                eval_status_str = evaluation.get("reviewStatus", "NEEDS_REVIEW")
                review_status = ReviewStatus.AUTO_APPROVED if (eval_status_str == "AUTO_APPROVED" and conf_float >= 0.85) else ReviewStatus.NEEDS_REVIEW

                eval_res = EvaluationResult(
                    extracted_answer_id=extracted.id,
                    score=float(evaluation.get("score", q.max_marks)),
                    max_score=float(evaluation.get("maxScore", q.max_marks)),
                    reasoning=evaluation.get("llmRationale", evaluation.get("reasoning", "")),
                    confidence=conf_float,
                    confidence_band=ConfidenceBand.HIGH if conf_float >= 0.85 else ConfidenceBand.MEDIUM,
                    review_status=review_status
                )
                db.add(eval_res)

            # 4. Finalize sheet and job status
            sheet_query = select(AnswerSheet).where(AnswerSheet.id == sheet_id)
            sheet = (await db.execute(sheet_query)).scalar_one_or_none()
            if sheet:
                sheet.status = SheetStatus.EVALUATED

            job.status = JobStatus.COMPLETED
            await db.commit()

        except Exception as e:
            # Log error and update job status
            print(f"[BackgroundEval] Error processing sheet {sheet_id}: {e}")
            async with AsyncSessionLocal() as err_db:
                # We need a new session to update the job status if the original one failed/rolled back
                job_query = select(ProcessingJob).where(ProcessingJob.answer_sheet_id == sheet_id).order_by(ProcessingJob.created_at.desc()).limit(1)
                job_res = await err_db.execute(job_query)
                job = job_res.scalar_one_or_none()
                if job:
                    job.status = JobStatus.FAILED
                    job.error_message = str(e)
                    await err_db.commit()

router = APIRouter(prefix="/api/v1/sheets", tags=["Sheets"])


ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}
ALLOWED_MIME_TYPES = {"application/pdf", "image/jpeg", "image/jpg", "image/png"}


class ApproveScoreRequest(BaseModel):
    score: float
    question_number: int = Field(1, ge=1)
    teacher_id: str


class FlagIssueRequest(BaseModel):
    reason: Optional[str] = "Teacher flagged issue"
    question_number: int = Field(1, ge=1)


class ReevaluationRequest(BaseModel):
    reason: str
    question_number: int = Field(1, ge=1)


@router.post("/upload")
async def upload_answer_sheets(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    exam_id: int = Form(...),
    student_roll: Optional[str] = Form(None),
    is_multi_page: bool = Form(False),
    db: AsyncSession = Depends(get_db)
):
    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No files provided for upload."
        )

    # Validate file formats
    for file in files:
        ext = ("." + file.filename.split(".")[-1]).lower() if "." in file.filename else ""
        content_type = file.content_type or ""
        if ext not in ALLOWED_EXTENSIONS and content_type not in ALLOWED_MIME_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file type '{file.filename}'. Please upload a PDF, JPG, or PNG file."
            )

    created_sheet_ids = []
    created_job_ids = []

    if is_multi_page:
        filenames = []
        raw_files = []
        for file in files:
            contents = await file.read()
            mime_type = file.content_type or ("application/pdf" if file.filename.endswith(".pdf") else "image/jpeg")
            filenames.append(file.filename)
            raw_files.append({"filename": file.filename, "bytes": contents, "mime_type": mime_type})

        joined_filenames = ", ".join(filenames)
        sheet = AnswerSheet(
            exam_id=exam_id,
            student_roll=student_roll or "2024CS001",
            original_filename=joined_filenames,
            page_count=len(files),
            status=SheetStatus.UPLOADED
        )
        db.add(sheet)
        await db.flush()

        # Create a processing job for this sheet
        job = ProcessingJob(
            answer_sheet_id=sheet.id,
            status=JobStatus.PENDING,
            stage="queued"
        )
        db.add(job)
        await db.flush()

        # Persist physical files and create SheetPage records
        sheet_dir = settings.upload_dir / f"sheet_{sheet.id}"
        sheet_dir.mkdir(parents=True, exist_ok=True)
        for idx, rf in enumerate(raw_files):
            safe_name = Path(rf["filename"]).name.replace(" ", "_")
            dest_file = sheet_dir / f"page_{idx + 1}_{safe_name}"
            with open(dest_file, "wb") as f_out:
                f_out.write(rf["bytes"])
            page = SheetPage(
                answer_sheet_id=sheet.id,
                page_number=idx + 1,
                file_path=str(dest_file.resolve()),
                ocr_raw_json=None
            )
            db.add(page)

        created_sheet_ids.append(sheet.id)
        created_job_ids.append(job.id)

        # Schedule background evaluation
        background_tasks.add_task(process_answer_sheet_task, sheet.id, exam_id)

    else:
        # For non-multi-page, each file is treated as a separate AnswerSheet
        for file in files:
            contents = await file.read()
            mime_type = file.content_type or ("application/pdf" if file.filename.endswith(".pdf") else "image/jpeg")

            sheet = AnswerSheet(
                exam_id=exam_id,
                student_roll=student_roll or "2024CS001",
                original_filename=file.filename,
                page_count=1,
                status=SheetStatus.UPLOADED
            )
            db.add(sheet)
            await db.flush()

            # Create a processing job for this sheet
            job = ProcessingJob(
                answer_sheet_id=sheet.id,
                status=JobStatus.PENDING,
                stage="queued"
            )
            db.add(job)
            await db.flush()

            # Persist physical file and create SheetPage record
            sheet_dir = settings.upload_dir / f"sheet_{sheet.id}"
            sheet_dir.mkdir(parents=True, exist_ok=True)
            safe_name = Path(file.filename).name.replace(" ", "_")
            dest_file = sheet_dir / f"page_1_{safe_name}"
            with open(dest_file, "wb") as f_out:
                f_out.write(contents)

            page = SheetPage(
                answer_sheet_id=sheet.id,
                page_number=1,
                file_path=str(dest_file.resolve()),
                ocr_raw_json=None
            )
            db.add(page)

            created_sheet_ids.append(sheet.id)
            created_job_ids.append(job.id)

            # Schedule background evaluation
            background_tasks.add_task(process_answer_sheet_task, sheet.id, exam_id)

    await db.commit()

    return {
        "message": "Files uploaded successfully. Evaluation is running in the background.",
        "sheet_ids": created_sheet_ids,
        "job_ids": created_job_ids
    }


@router.get("/list")
async def list_graded_sheets(
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Returns a list of graded answer sheets with filtered status.
    Status options: ALL, AUTO_APPROVED, NEEDS_REVIEW
    """
    # Base query: join AnswerSheet -> ExtractedAnswer -> EvaluationResult
    query = (
        select(AnswerSheet)
        .join(ExtractedAnswer)
        .join(EvaluationResult)
        .options(
            selectinload(AnswerSheet.exam),
            selectinload(AnswerSheet.extracted_answers).selectinload(ExtractedAnswer.evaluation_result)
        )
    )

    if status == "AUTO_APPROVED":
        query = query.where(EvaluationResult.review_status == ReviewStatus.AUTO_APPROVED)
    elif status == "NEEDS_REVIEW":
        query = query.where(
            EvaluationResult.review_status.in_([ReviewStatus.NEEDS_REVIEW, ReviewStatus.FLAGGED])
        )

    result = await db.execute(query)
    sheets = result.scalars().all()

    out = []
    for s in sheets:
        # We assume one evaluation result per sheet for the summary list
        # (usually it's per question, so we take the first one for the summary)
        first_eval = s.extracted_answers[0].evaluation_result if s.extracted_answers else None

        # Calculate total and obtained marks
        obtained = sum(ea.evaluation_result.score for ea in s.extracted_answers if ea.evaluation_result)
        total = sum(ea.evaluation_result.max_score for ea in s.extracted_answers if ea.evaluation_result) or 10.0

        out.append({
            "sheetId": s.id,
            "studentName": s.student.name if s.student else "Unknown",
            "studentRoll": s.student_roll or "N/A",
            "examName": s.exam.title if s.exam else "Unknown Exam",
            "examId": s.exam_id,
            "obtainedMarks": round(obtained, 2),
            "totalMarks": round(total, 2),
            "percentage": round((obtained / total) * 100, 1) if total > 0 else 0,
            "evaluationDate": s.created_at.isoformat(),
            "status": s.status.name,
            "confidence": int(first_eval.confidence * 100) if first_eval else 0,
            "reviewStatus": first_eval.review_status.name if first_eval else "PENDING"
        })

    return out

@router.get("/{sheet_id}/file")
async def get_sheet_file(sheet_id: int, db: AsyncSession = Depends(get_db)):
    query = (
        select(SheetPage)
        .where(SheetPage.answer_sheet_id == sheet_id)
        .order_by(SheetPage.page_number.asc())
    )
    result = await db.execute(query)
    page = result.scalars().first()
    if not page or not page.file_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No document file found for answer sheet {sheet_id}."
        )

    file_path = Path(page.file_path)
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File not found on server disk: {file_path.name}"
        )

    ext = file_path.suffix.lower()
    media_type = (
        "application/pdf" if ext == ".pdf"
        else "image/jpeg" if ext in [".jpg", ".jpeg"]
        else "image/png" if ext == ".png"
        else "application/octet-stream"
    )

    return FileResponse(
        path=str(file_path),
        media_type=media_type,
        content_disposition_type="inline",
        filename=file_path.name
    )


@router.get("/{sheet_id}/pages/{page_number}/file")
async def get_sheet_page_file(sheet_id: int, page_number: int, db: AsyncSession = Depends(get_db)):
    query = (
        select(SheetPage)
        .where(SheetPage.answer_sheet_id == sheet_id, SheetPage.page_number == page_number)
    )
    result = await db.execute(query)
    page = result.scalar_one_or_none()
    if not page or not page.file_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Page {page_number} not found for answer sheet {sheet_id}."
        )

    file_path = Path(page.file_path)
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File not found on server disk: {file_path.name}"
        )

    ext = file_path.suffix.lower()
    media_type = (
        "application/pdf" if ext == ".pdf"
        else "image/jpeg" if ext in [".jpg", ".jpeg"]
        else "image/png" if ext == ".png"
        else "application/octet-stream"
    )

    return FileResponse(
        path=str(file_path),
        media_type=media_type,
        content_disposition_type="inline",
        filename=file_path.name
    )


@router.get("/reevaluations")
async def list_reevaluation_requests(db: AsyncSession = Depends(get_db)):
    """Returns a list of all evaluation results flagged for re-evaluation by students."""
    query = (
        select(EvaluationResult)
        .join(ConfidenceFlag, EvaluationResult.id == ConfidenceFlag.evaluation_result_id)
        .join(ExtractedAnswer, EvaluationResult.extracted_answer_id == ExtractedAnswer.id)
        .join(AnswerSheet, ExtractedAnswer.answer_sheet_id == AnswerSheet.id)
        .join(Exam, AnswerSheet.exam_id == Exam.id)
        .where(ConfidenceFlag.flag_type == "student_reeval_request")
        .order_by(ConfidenceFlag.created_at.desc())
    )
    result = await db.execute(query)
    evals = result.scalars().all()

    out = []
    for ev in evals:
        # Get the flag detail
        flag_query = select(ConfidenceFlag).where(
            ConfidenceFlag.evaluation_result_id == ev.id,
            ConfidenceFlag.flag_type == "student_reeval_request"
        ).order_by(ConfidenceFlag.created_at.desc())
        flag = (await db.execute(flag_query)).scalar_one_or_none()

        # Get related sheet/exam
        sheet = await db.get(AnswerSheet, ev.extracted_answer.answer_sheet_id)
        exam = await db.get(Exam, sheet.exam_id)

        out.append({
            "id": f"R-{ev.id:03d}",
            "student": sheet.student_roll or "N/A",
            "subject": exam.title if exam else "Unknown Exam",
            "testId": f"T-{sheet.id:03d}",
            "reason": flag.detail if flag else "No reason provided",
            "status": "Pending",
            "date": flag.created_at.strftime("%b %d, %Y") if flag else "N/A"
        })
    return out


@router.get("/{sheet_id}/review")

async def get_sheet_review(sheet_id: str, db: AsyncSession = Depends(get_db)):
    if sheet_id == "next":
        query = (
            select(AnswerSheet)
            .join(ExtractedAnswer, AnswerSheet.id == ExtractedAnswer.answer_sheet_id)
            .join(EvaluationResult, ExtractedAnswer.id == EvaluationResult.extracted_answer_id)
            .options(
                selectinload(AnswerSheet.exam),
                selectinload(AnswerSheet.pages),
                selectinload(AnswerSheet.extracted_answers).selectinload(ExtractedAnswer.evaluation_result)
            )
            .where(EvaluationResult.review_status.in_([ReviewStatus.NEEDS_REVIEW, ReviewStatus.FLAGGED]))
            .order_by(AnswerSheet.created_at.asc())
            .limit(1)
        )
    else:
        try:
            sid = int(sheet_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid sheet_id")

        query = (
            select(AnswerSheet)
            .options(
                selectinload(AnswerSheet.exam),
                selectinload(AnswerSheet.pages),
                selectinload(AnswerSheet.extracted_answers).selectinload(ExtractedAnswer.evaluation_result)
            )
            .where(AnswerSheet.id == sid)
        )

    result = await db.execute(query)
    sheet = result.scalar_one_or_none()

    if not sheet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Answer sheet not found." if sheet_id == "next" else f"Answer sheet with ID {sheet_id} not found."
        )

    # Get extracted answers and their evaluations
    extracted_answers_data = []
    if sheet.extracted_answers:
        for ea in sheet.extracted_answers:
            ev = ea.evaluation_result
            extracted_answers_data.append({
                "questionNumber": ea.question_number,
                "rawText": ea.raw_text,
                "score": ev.score if ev else 0.0,
                "maxScore": ev.max_score if ev else 10.0,
                "aiConfidence": int(ev.confidence * 100) if ev and ev.confidence <= 1.0 else int(ev.confidence) if ev else 78,
                "llmRationale": ev.reasoning if ev else "",
                "reasoning": ev.reasoning if ev else "",
                "missingConcepts": ["Review notation clarity."] if (ev and ev.confidence < 0.85) else [],
                "reviewStatus": ev.review_status.name if ev else "NEEDS_REVIEW",
            })

    conf_pct = 78
    if sheet.extracted_answers and sheet.extracted_answers[0].evaluation_result:
        ev = sheet.extracted_answers[0].evaluation_result
        conf_pct = int(ev.confidence * 100) if ev.confidence <= 1.0 else int(ev.confidence)

    file_urls = []
    file_types = []
    if sheet.pages:
        for p in sheet.pages:
            file_urls.append(f"/api/v1/sheets/{sheet.id}/pages/{p.page_number}/file")
            p_ext = Path(p.file_path).suffix.lower() if p.file_path else ""
            file_types.append(
                "application/pdf" if p_ext == ".pdf"
                else "image/jpeg" if p_ext in [".jpg", ".jpeg"]
                else "image/png" if p_ext == ".png"
                else "application/octet-stream"
            )
    else:
        file_urls = [f"/api/v1/sheets/{sheet.id}/file"]
        ext = ("." + sheet.original_filename.split(".")[-1]).lower() if sheet.original_filename and "." in sheet.original_filename else ".pdf"
        file_types = ["application/pdf" if ext == ".pdf" else "image/jpeg"]

    return {
        "sheetId": sheet.id,
        "examId": sheet.exam_id,
        "examTitle": sheet.exam.title if sheet.exam else f"Exam #{sheet.exam_id}",
        "studentRoll": sheet.student_roll or "N/A",
        "fileName": sheet.original_filename,
        "evaluations": extracted_answers_data,
        "fileUrls": file_urls,
        "fileTypes": file_types,
        "fileUrl": file_urls[0] if file_urls else None,
        "fileType": file_types[0] if file_types else "application/pdf"
    }


@router.post("/{sheet_id}/approve")
async def approve_score(
    sheet_id: int,
    req: ApproveScoreRequest,
    db: AsyncSession = Depends(get_db)
):
    query = (
        select(EvaluationResult)
        .join(ExtractedAnswer)
        .where(ExtractedAnswer.answer_sheet_id == sheet_id)
        .where(ExtractedAnswer.question_number == req.question_number)
    )
    result = await db.execute(query)
    eval_res = result.scalar_one_or_none()

    if not eval_res:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evaluation for question {req.question_number} on sheet {sheet_id} not found."
        )

    old_score = eval_res.score
    eval_res.score = req.score

    if abs(old_score - req.score) > 0.01:
        eval_res.review_status = ReviewStatus.OVERRIDDEN
        override = TeacherOverride(
            evaluation_result_id=eval_res.id,
            teacher_id=req.teacher_id or "teacher1",
            old_score=old_score,
            new_score=req.score,
            override_reason="Teacher manual score approval & adjustment."
        )
        db.add(override)
    else:
        eval_res.review_status = ReviewStatus.REVIEWED

    # Update sheet status to evaluated if all are done (simplified)
    sheet_query = select(AnswerSheet).where(AnswerSheet.id == sheet_id)
    sheet = (await db.execute(sheet_query)).scalar_one_or_none()
    if sheet:
        sheet.status = SheetStatus.EVALUATED

    await db.commit()

    return {
        "message": f"Score for Q{req.question_number} approved successfully! Final score: {req.score}",
        "sheet_id": sheet_id,
        "question_number": req.question_number,
        "score": req.score,
        "reviewStatus": "APPROVED"
    }


@router.post("/{sheet_id}/flag")
async def flag_issue(
    sheet_id: int,
    req: FlagIssueRequest,
    db: AsyncSession = Depends(get_db)
):
    query = (
        select(EvaluationResult)
        .join(ExtractedAnswer)
        .where(ExtractedAnswer.answer_sheet_id == sheet_id)
        .where(ExtractedAnswer.question_number == req.question_number)
    )
    result = await db.execute(query)
    eval_res = result.scalar_one_or_none()

    if not eval_res:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evaluation for question {req.question_number} on sheet {sheet_id} not found."
        )

    eval_res.review_status = ReviewStatus.FLAGGED
    flag = ConfidenceFlag(
        evaluation_result_id=eval_res.id,
        flag_type="teacher_flag",
        detail=req.reason or "Flagged by teacher for manual re-checking."
    )
    db.add(flag)

    await db.commit()

    return {
        "message": "Issue flagged successfully and saved to database.",
        "sheet_id": sheet_id,
        "question_number": req.question_number,
        "reviewStatus": "FLAGGED"
    }


@router.post("/{sheet_id}/reevaluate")
async def request_reevaluation(
    sheet_id: int,
    req: ReevaluationRequest,
    db: AsyncSession = Depends(get_db)
):
    query = (
        select(EvaluationResult)
        .join(ExtractedAnswer)
        .where(ExtractedAnswer.answer_sheet_id == sheet_id)
        .where(ExtractedAnswer.question_number == req.question_number)
    )
    result = await db.execute(query)
    eval_res = result.scalar_one_or_none()

    if not eval_res:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evaluation for question {req.question_number} on sheet {sheet_id} not found."
        )

    eval_res.review_status = ReviewStatus.NEEDS_REVIEW
    flag = ConfidenceFlag(
        evaluation_result_id=eval_res.id,
        flag_type="student_reeval_request",
        detail=req.reason
    )
    db.add(flag)

    await db.commit()

    return {
        "message": "Re-evaluation request submitted successfully.",
        "sheet_id": sheet_id,
        "question_number": req.question_number,
        "reviewStatus": "NEEDS_REVIEW"
    }
