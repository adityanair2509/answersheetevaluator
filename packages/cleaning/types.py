"""
packages/cleaning/types.py

Lightweight dataclasses for the text cleaning / standardization pipeline.
These types flow between normalize → question_splitter → downstream RAG ingestion.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class NormalizedText:
    """
    Result of normalizing a raw OCR text string.

    Attributes:
        original:     The unmodified input text.
        cleaned:      Text after OCR artifact removal and whitespace normalization.
        issues_found: Human-readable list of problems detected and fixed.
    """

    original: str
    cleaned: str
    issues_found: list[str] = field(default_factory=list)


@dataclass
class QuestionSegment:
    """
    A single question's text extracted from a larger answer-key or OCR dump.

    Attributes:
        question_number: Detected question number (1-indexed).
        raw_text:        The original text slice for this question (untouched).
        cleaned_text:    The cleaned/normalized version of the text.
        label_format:    The literal label string that was detected (e.g. "Q1.", "1)", "Question 3").
                         Empty string if no explicit label was found.
    """

    question_number: int
    raw_text: str
    cleaned_text: str
    label_format: str = ""
