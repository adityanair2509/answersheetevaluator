"""
packages/ocr/segment.py

Map OCR text blocks to question numbers.

The segmenter works in two passes:
  Pass 1 — scan every block for an explicit question label (regex).
  Pass 2 — assign unlabelled blocks to the most recent labelled question.

Supported label patterns (case-insensitive):
  "1."   "1)"   "1:"   "Q1"   "Q.1"   "Q1."   "Question 1"
  Multi-digit: "10.", "Q10", etc.

Exports:
    detect_question_number(text) → int | None
    assign_blocks_to_questions(blocks, known_questions) → list[SegmentedAnswer]
"""
from __future__ import annotations

import re
import statistics
from collections import defaultdict

from packages.ocr.types import OCRBlock, SegmentedAnswer

# ---------------------------------------------------------------------------
# Question label regex
# Matches at the start of a stripped string or after leading whitespace.
# Groups: (question_number_str)
# ---------------------------------------------------------------------------

_LABEL_PATTERN = re.compile(
    r"""
    (?:^|\s)                 # start of string or whitespace
    (?:
        [Qq](?:uestion\s*)?  # "Q", "q", "Question", "question"
        [.\s]?               # optional separator
        (\d{1,3})            # ← group 1: the number
        (?:\s|$|[.):\s])     # must be followed by space/end/separator (not another digit)
    |
        (\d{1,3})            # ← group 2: bare number
        \s*[):]              # followed by ) or : (NOT period — period handled separately)
    |
        (\d{1,3})            # ← group 3: bare number followed by period
        \.                   # literal period
        (?!\d)               # NOT followed by another digit (avoid "2.4", "10.5")
        \s                   # must be followed by whitespace
    )
    """,
    re.VERBOSE | re.IGNORECASE,
)


def detect_question_number(text: str) -> int | None:
    """
    Return the question number found at the start of `text`, or None.

    Only the *first* match is used. The match must occur within the first
    60 characters of the stripped text to avoid false-positives mid-sentence
    (e.g. "The concentration is 2.4 mol/L").

    Examples:
        "1. The process …"   → 1
        "Q2 Newton's law …"  → 2
        "Question 3) Water …"→ 3
        "10. Explain …"      → 10
        "stored in glucose …"→ None
    """
    stripped = text.strip()
    # Only look in the first 60 chars to avoid mid-sentence numbers
    prefix = stripped[:60]
    match = _LABEL_PATTERN.search(prefix)
    if match is None:
        return None
    # Groups: 1=Q-style, 2=bare number + ) or :, 3=bare number + period (not decimal)
    num_str = match.group(1) or match.group(2) or match.group(3)
    try:
        return int(num_str)
    except (ValueError, TypeError):
        return None


def assign_blocks_to_questions(
    blocks: list[OCRBlock],
    known_questions: list[int] | None = None,
) -> list[SegmentedAnswer]:
    """
    Group OCR blocks into per-question segments.

    Algorithm:
        - Iterate blocks in order (assumed top-to-bottom / reading order).
        - If a block starts with a question label, open a new segment.
        - Otherwise, append the block to the current open segment.
        - Blocks that appear before any labelled block are collected under
          question 0 (unknown) and either merged or discarded.

    Args:
        blocks:          Ordered list of OCR blocks from the Vision API.
        known_questions: Optional list of expected question numbers.
                         If provided, only these numbers will be retained;
                         any detected number not in the list is treated as
                         a mis-detection and the block is appended to the
                         previous segment instead.

    Returns:
        List of SegmentedAnswer, one per detected question number,
        sorted by question_number ascending.
        Blocks with no question label (before the first label) are dropped.
    """
    # Map: question_number → list of contributing OCRBlocks
    question_blocks: dict[int, list[OCRBlock]] = defaultdict(list)
    label_detected: dict[int, bool] = {}

    current_q: int | None = None
    known_set = set(known_questions) if known_questions else None

    for block in blocks:
        detected = detect_question_number(block.text)

        if detected is not None:
            # Reject if it's outside the expected question set
            if known_set is not None and detected not in known_set:
                # Treat as continuation of current question
                if current_q is not None:
                    question_blocks[current_q].append(block)
                continue

            current_q = detected
            label_detected[current_q] = True
            # Strip the label prefix from the text before storing
            stripped_text = _strip_label(block.text, detected)
            block_copy = OCRBlock(
                text=stripped_text,
                confidence=block.confidence,
                bounds=block.bounds,
                page=block.page,
            )
            question_blocks[current_q].append(block_copy)
        else:
            if current_q is not None:
                question_blocks[current_q].append(block)
            # else: pre-label block — discard (header/footer text)

    # Build SegmentedAnswer objects
    results: list[SegmentedAnswer] = []
    for q_num in sorted(question_blocks.keys()):
        q_blocks = question_blocks[q_num]
        if not q_blocks:
            continue

        merged_text = "\n".join(b.text.strip() for b in q_blocks if b.text.strip())
        bboxes = [b.bounds.to_dict() for b in q_blocks]
        confidences = [b.confidence for b in q_blocks]
        avg_conf = statistics.mean(confidences) if confidences else 1.0
        first_page = q_blocks[0].page

        results.append(
            SegmentedAnswer(
                question_number=q_num,
                raw_text=merged_text,
                bounding_boxes=bboxes,
                ocr_confidence=round(avg_conf, 4),
                page=first_page,
                label_detected=label_detected.get(q_num, False),
            )
        )

    return results


# ── Internal helpers ──────────────────────────────────────────────────────────


def _strip_label(text: str, question_number: int) -> str:
    """
    Remove the question label prefix from the beginning of a block's text.

    For example:
        "1. The process …" → "The process …"
        "Q3) Water cycle …" → "Water cycle …"
    """
    # Build a pattern that matches the specific number at the start
    pattern = re.compile(
        rf"""
        ^\s*                         # optional leading whitespace
        (?:
            [Qq](?:uestion\s*)?      # Q / Question
            [.\s]?
            {re.escape(str(question_number))}
        |
            {re.escape(str(question_number))}
            \s*[.):]
        )
        \s*                          # trailing whitespace after label
        """,
        re.VERBOSE | re.IGNORECASE,
    )
    result = pattern.sub("", text, count=1)
    return result.strip()
