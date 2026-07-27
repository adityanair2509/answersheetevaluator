"""
packages/cleaning — OCR artifact removal, normalization, question splitting.

Public API:
    normalize_text(raw) → NormalizedText
    fix_common_ocr_errors(text) → (str, list[str])
    standardize_whitespace(text) → str
    split_into_segments(text, expected_questions) → list[QuestionSegment]
    parse_question_label(text) → (int | None, str)
"""

from packages.cleaning.normalize import (
    fix_common_ocr_errors,
    normalize_text,
    standardize_whitespace,
)
from packages.cleaning.number_parser import parse_question_label
from packages.cleaning.question_splitter import split_into_segments
from packages.cleaning.types import NormalizedText, QuestionSegment

__all__ = [
    "NormalizedText",
    "QuestionSegment",
    "fix_common_ocr_errors",
    "normalize_text",
    "parse_question_label",
    "split_into_segments",
    "standardize_whitespace",
]
