"""
packages/ocr/pipeline.py

Top-level OCR pipeline orchestrator.

Ties together:
    preprocess → run_ocr → segment

Public API:
    run_ocr_pipeline(image_path, question_numbers, ocr_client) → list[SegmentedAnswer]
    run_ocr_pipeline_from_array(image, ...)                    → list[SegmentedAnswer]

The pipeline is synchronous — callers (Day 6-7 background job runner) are
expected to wrap it in ``asyncio.to_thread()`` or a ThreadPoolExecutor.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from packages.common.logging import get_logger
from packages.ocr.preprocess import preprocess_from_array, preprocess_sheet
from packages.ocr.segment import assign_blocks_to_questions
from packages.ocr.types import OCRResult, SegmentedAnswer
from packages.ocr.vision_client import BaseOCRClient, MockVisionClient, run_ocr

logger = get_logger(__name__)


# ── Main pipeline entry points ────────────────────────────────────────────────


def run_ocr_pipeline(
    image_path: str | Path,
    question_numbers: list[int] | None = None,
    ocr_client: BaseOCRClient | None = None,
    page: int = 1,
) -> list[SegmentedAnswer]:
    """
    Full OCR pipeline for one page image file.

    Stages:
        1. Preprocess  — deskew, denoise, binarize, crop (OpenCV)
        2. OCR         — call Vision API (or mock) to get text blocks
        3. Segment     — map blocks to question numbers

    Args:
        image_path:       Path to the image file (JPEG, PNG, TIFF, etc.)
        question_numbers: Expected question numbers for the exam.
                          If provided, only these numbers are retained;
                          spurious detections are treated as continuation text.
        ocr_client:       OCR backend to use. Defaults to MockVisionClient when
                          not provided (safe for unit tests without credentials).
        page:             1-indexed page number attached to OCR blocks.

    Returns:
        List of SegmentedAnswer, one per detected question, sorted numerically.

    Raises:
        FileNotFoundError: if image_path does not exist.
        ValueError:        if the image cannot be decoded.
    """
    client = ocr_client or MockVisionClient()

    logger.debug("ocr_pipeline.start", path=str(image_path), page=page)

    # Stage 1: preprocessing
    preprocessed = preprocess_sheet(image_path)
    logger.debug(
        "ocr_pipeline.preprocessed",
        rotation_deg=preprocessed.rotation_deg,
        quality=preprocessed.quality_score,
    )

    # Stage 2: OCR
    ocr_result: OCRResult = run_ocr(preprocessed.image, client, page=page)
    logger.debug(
        "ocr_pipeline.ocr_done",
        blocks=len(ocr_result.blocks),
        provider=type(client).__name__,
    )

    # Stage 3: segmentation
    answers = assign_blocks_to_questions(ocr_result.blocks, known_questions=question_numbers)
    logger.debug("ocr_pipeline.segmented", questions_found=len(answers))

    return answers


def run_ocr_pipeline_from_array(
    image: Any,  # np.ndarray
    question_numbers: list[int] | None = None,
    ocr_client: BaseOCRClient | None = None,
    page: int = 1,
    source_path: str = "",
) -> list[SegmentedAnswer]:
    """
    Full OCR pipeline operating on an in-memory numpy array.

    Useful for:
    - Unit tests (pass a synthetic array without touching disk)
    - PDF processing (each page is already decoded to a numpy array by pdf2image)

    Args:
        image:            numpy ndarray (uint8, grayscale or BGR).
        question_numbers: See ``run_ocr_pipeline``.
        ocr_client:       See ``run_ocr_pipeline``.
        page:             1-indexed page number.
        source_path:      Original source path string (for logging/metadata only).

    Returns:
        List of SegmentedAnswer.
    """
    client = ocr_client or MockVisionClient()

    logger.debug("ocr_pipeline_array.start", source=source_path, page=page)

    # Stage 1: preprocessing (skip load step)
    preprocessed = preprocess_from_array(image, source_path=source_path)
    logger.debug(
        "ocr_pipeline_array.preprocessed",
        rotation_deg=preprocessed.rotation_deg,
        quality=preprocessed.quality_score,
    )

    # Stage 2: OCR
    ocr_result: OCRResult = run_ocr(preprocessed.image, client, page=page)
    logger.debug(
        "ocr_pipeline_array.ocr_done",
        blocks=len(ocr_result.blocks),
        provider=type(client).__name__,
    )

    # Stage 3: segmentation
    answers = assign_blocks_to_questions(ocr_result.blocks, known_questions=question_numbers)
    logger.debug("ocr_pipeline_array.segmented", questions_found=len(answers))

    return answers


# ── OCR result metadata helper ────────────────────────────────────────────────


def ocr_result_to_page_json(ocr_result: OCRResult) -> dict:
    """
    Serialise an OCRResult to the JSON dict stored in ``sheet_pages.ocr_raw_json``.
    Includes both the raw Vision response and a clean summary for debugging.
    """
    return {
        "page": ocr_result.page,
        "block_count": len(ocr_result.blocks),
        "full_text_preview": ocr_result.full_text[:500],
        "raw_response": ocr_result.raw_response,
    }
