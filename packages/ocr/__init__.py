"""
packages/ocr

OCR pipeline: OpenCV preprocessing → Google Vision (or mock) → answer segmentation.

Public API
----------
from packages.ocr import (
    # Pipeline entry points
    run_ocr_pipeline,            # file path → list[SegmentedAnswer]
    run_ocr_pipeline_from_array, # numpy array → list[SegmentedAnswer]

    # OCR clients
    get_ocr_client,              # factory: returns Google or Mock client
    MockVisionClient,            # deterministic mock (no API calls)
    GoogleVisionClient,          # real Vision API wrapper

    # Types
    OCRBlock,
    OCRResult,
    SegmentedAnswer,
    PreprocessedImage,
    BoundingPoly,

    # Lower-level helpers
    preprocess_sheet,            # file path → PreprocessedImage
    preprocess_from_array,       # numpy array → PreprocessedImage
    run_ocr,                     # numpy array + client → OCRResult
    detect_question_number,      # text → int | None
    assign_blocks_to_questions,  # blocks → list[SegmentedAnswer]
)
"""

from __future__ import annotations

from packages.ocr.pipeline import run_ocr_pipeline, run_ocr_pipeline_from_array
from packages.ocr.preprocess import preprocess_from_array, preprocess_sheet
from packages.ocr.segment import assign_blocks_to_questions, detect_question_number
from packages.ocr.types import (
    BoundingPoly,
    OCRBlock,
    OCRResult,
    PreprocessedImage,
    SegmentedAnswer,
)
from packages.ocr.vision_client import (
    GoogleVisionClient,
    GoogleVisionRestClient,
    MockVisionClient,
    get_ocr_client,
    run_ocr,
)

__all__ = [
    # Pipeline
    "run_ocr_pipeline",
    "run_ocr_pipeline_from_array",
    # Preprocessing
    "preprocess_sheet",
    "preprocess_from_array",
    # Vision clients
    "get_ocr_client",
    "MockVisionClient",
    "GoogleVisionClient",
    "GoogleVisionRestClient",
    "run_ocr",
    # Segmentation
    "detect_question_number",
    "assign_blocks_to_questions",
    # Types
    "OCRBlock",
    "OCRResult",
    "SegmentedAnswer",
    "PreprocessedImage",
    "BoundingPoly",
]
