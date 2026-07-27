"""
packages/cleaning/question_splitter.py

Split a block of text (answer key or OCR output) into per-question segments.

This module is used for both:
  - Teacher answer keys (well-formatted, numbered) → RAG chunking
  - Student answer OCR text (noisy, may lack labels) → post-OCR cleanup

The splitter is intentionally simple and regex-based.  It does NOT use an LLM.

Exports:
    split_into_segments(text, expected_questions) → list[QuestionSegment]
"""

from __future__ import annotations

import re

from packages.cleaning.normalize import normalize_text
from packages.cleaning.number_parser import parse_question_label
from packages.cleaning.types import QuestionSegment


def split_into_segments(
    text: str,
    expected_questions: list[int] | None = None,
) -> list[QuestionSegment]:
    """
    Split *text* into per-question segments.

    Algorithm:
        1. Split text into lines.
        2. Scan each line for a question label (via ``parse_question_label``).
        3. When a new label is found, close the previous segment and start a
           new one.
        4. Lines before any label are collected under question 0 (discarded
           unless no labels are found at all).
        5. If *expected_questions* is provided, only those question numbers
           are accepted; any other detected number is treated as body text.

    Fallback behaviour:
        - If no question labels are detected at all, the entire text is
          returned as a single segment with ``question_number=1``.

    Args:
        text:               The raw text to split.
        expected_questions:  Optional list of expected question numbers.
                             Restricts which numbers are accepted as labels.

    Returns:
        List of ``QuestionSegment`` sorted by question_number ascending.
    """
    if not text or not text.strip():
        return []

    expected_set = set(expected_questions) if expected_questions else None
    lines = text.splitlines()

    # Accumulator: question_number → (label_format, [line_strings])
    segments: dict[int, tuple[str, list[str]]] = {}
    current_q: int | None = None

    for line in lines:
        stripped = line.strip()
        if not stripped:
            # Preserve blank lines within the current segment
            if current_q is not None:
                segments[current_q][1].append("")
            continue

        q_num, label = parse_question_label(stripped)

        if q_num is not None:
            # Reject if outside expected set
            if expected_set is not None and q_num not in expected_set:
                # Treat as body text of current question
                if current_q is not None:
                    segments[current_q][1].append(stripped)
                continue

            # Start a new segment
            current_q = q_num
            # Strip the label from the first line of the segment
            body = _strip_label_prefix(stripped, label)
            if current_q not in segments:
                segments[current_q] = (label, [])
            if body:
                segments[current_q][1].append(body)
        else:
            if current_q is not None:
                segments[current_q][1].append(stripped)
            # else: pre-label line — discard (header/instructions text)

    # Fallback: no labels found → treat entire text as Q1
    if not segments:
        normalized = normalize_text(text)
        return [
            QuestionSegment(
                question_number=1,
                raw_text=text.strip(),
                cleaned_text=normalized.cleaned,
                label_format="",
            )
        ]

    # Build QuestionSegment objects
    results: list[QuestionSegment] = []
    for q_num in sorted(segments.keys()):
        label_fmt, body_lines = segments[q_num]
        raw = "\n".join(body_lines).strip()
        if not raw:
            continue
        normalized = normalize_text(raw)
        results.append(
            QuestionSegment(
                question_number=q_num,
                raw_text=raw,
                cleaned_text=normalized.cleaned,
                label_format=label_fmt,
            )
        )

    return results


# ── Internal helpers ──────────────────────────────────────────────────────────


def _strip_label_prefix(text: str, label: str) -> str:
    """
    Remove the matched label string from the beginning of *text*.

    Handles slight whitespace variations between the label and the body.
    """
    if not label:
        return text
    # Escape the label for use in regex, then allow flexible whitespace
    pattern = re.compile(
        r"^\s*" + re.escape(label) + r"\s*",
        re.IGNORECASE,
    )
    result = pattern.sub("", text, count=1)
    return result.strip()
