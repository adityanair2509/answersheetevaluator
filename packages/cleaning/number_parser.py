"""
packages/cleaning/number_parser.py

Regex-based detection of question labels in text.

Supports common handwritten / printed formats:
    "1."   "1)"   "1:"   "(1)"
    "Q1"   "Q.1"  "Q1."  "Q 1"
    "Question 1"   "question 1."
    Multi-digit: "10.", "Q12", etc.

Exports:
    QUESTION_PATTERNS  — compiled regex list (most-specific first)
    parse_question_label(text) → (int | None, str)
"""

from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# Compiled patterns — ordered from most specific (least ambiguous) to most
# generic (most likely to false-positive).
#
# Each pattern captures:
#   group("num")  — the question number digits
#   group("label") — the full label string that was matched
# ---------------------------------------------------------------------------

QUESTION_PATTERNS: list[re.Pattern[str]] = [
    # "Question 1", "question 1.", "Question 10:"
    re.compile(
        r"(?P<label>[Qq]uestion\s*(?P<num>\d{1,3})\s*[.):]?)",
        re.IGNORECASE,
    ),
    # "Q1.", "Q.1", "Q 1", "Q1)", "Q1:"
    re.compile(
        r"(?P<label>[Qq]\s*\.?\s*(?P<num>\d{1,3})\s*[.):]?)",
    ),
    # "(1)", "(10)"
    re.compile(
        r"(?P<label>\(\s*(?P<num>\d{1,3})\s*\))",
    ),
    # "1)", "10)"
    re.compile(
        r"(?P<label>(?P<num>\d{1,3})\s*\))",
    ),
    # "1:", "10:"
    re.compile(
        r"(?P<label>(?P<num>\d{1,3})\s*:)",
    ),
    # "1. " — bare number + period + space (NOT a decimal like 2.4)
    re.compile(
        r"(?P<label>(?P<num>\d{1,3})\s*\.)(?=\s|$)",
    ),
]


def parse_question_label(text: str) -> tuple[int | None, str]:
    """
    Extract a question number from the beginning of *text*.

    Only searches the first 80 characters to avoid mid-sentence false
    positives (e.g. "the ratio is 2.5 to 1").

    Returns:
        (question_number, matched_label_string)
        or (None, "") if no label was found.

    Examples:
        >>> parse_question_label("1. Define osmosis.")
        (1, '1.')
        >>> parse_question_label("Q3) Explain Newton's laws.")
        (3, 'Q3)')
        >>> parse_question_label("The cell membrane …")
        (None, '')
    """
    prefix = text.lstrip()[:80]

    for pattern in QUESTION_PATTERNS:
        match = pattern.match(prefix)
        if match is None:
            continue
        num_str = match.group("num")
        label_str = match.group("label").strip()
        try:
            return int(num_str), label_str
        except (ValueError, TypeError):
            continue

    return None, ""
