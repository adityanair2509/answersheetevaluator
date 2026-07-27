"""
packages/cleaning/normalize.py

OCR text cleanup utilities.

These functions fix common artifacts left by handwriting OCR engines
(Google Vision, PaddleOCR, TrOCR) without changing the semantic meaning
of the text.  The goal is to produce cleaner input for downstream RAG
chunking and LLM evaluation prompts.

Exports:
    normalize_text(raw) → NormalizedText
    fix_common_ocr_errors(text) → str
    standardize_whitespace(text) → str
"""

from __future__ import annotations

import re
import unicodedata

from packages.cleaning.types import NormalizedText

# ---------------------------------------------------------------------------
# OCR error correction table
# Keys are regex patterns, values are replacement strings.
# Order matters — more specific patterns first.
# ---------------------------------------------------------------------------

_OCR_FIXES: list[tuple[re.Pattern[str], str, str]] = [
    # "l." or "l)" at line start → "1." / "1)" (common misread of digit 1)
    (re.compile(r"^l(?=[.)])", re.MULTILINE), "1", "l→1 at line start"),
    # "O" surrounded by digits → "0"
    (re.compile(r"(?<=\d)O(?=\d)"), "0", "O→0 between digits"),
    # "|" at line start followed by digit → "1" (pipe misread)
    (re.compile(r"^\|(?=\d)", re.MULTILINE), "1", "|→1 at line start"),
    # "ll" → "11" when inside digit runs (e.g. "ll.5" → "11.5")
    (re.compile(r"(?<=\d)ll(?=\d)"), "11", "ll→11 between digits"),
    # Smart quotes → straight quotes
    (re.compile(r"[\u2018\u2019]"), "'", "smart single quote"),
    (re.compile(r"[\u201C\u201D]"), '"', "smart double quote"),
    # Em / en dashes → regular hyphen
    (re.compile(r"[\u2013\u2014]"), "-", "em/en dash → hyphen"),
    # Ellipsis character → three dots
    (re.compile(r"\u2026"), "...", "ellipsis character"),
]

# Characters to strip entirely (zero-width spaces, BOM, soft-hyphens)
_STRIP_CHARS = re.compile(r"[\u200b\u200c\u200d\ufeff\u00ad\ufff9\ufffa\ufffb]")


def fix_common_ocr_errors(text: str) -> tuple[str, list[str]]:
    """
    Apply OCR-specific character-level fixes.

    Returns:
        (corrected_text, list_of_issues_found)
    """
    issues: list[str] = []
    result = text

    for pattern, replacement, description in _OCR_FIXES:
        if pattern.search(result):
            result = pattern.sub(replacement, result)
            issues.append(description)

    return result, issues


def standardize_whitespace(text: str) -> str:
    """
    Normalize whitespace without destroying paragraph structure.

    Rules:
      - Collapse multiple spaces/tabs into a single space.
      - Collapse 3+ consecutive newlines into 2 (preserve paragraph breaks).
      - Strip trailing whitespace on each line.
      - Strip leading/trailing whitespace on the whole string.
    """
    # Collapse tabs and multiple spaces (but not newlines) into single space
    text = re.sub(r"[^\S\n]+", " ", text)
    # Strip trailing spaces on each line
    text = re.sub(r" +$", "", text, flags=re.MULTILINE)
    # Collapse 3+ newlines into exactly 2 (one blank line = paragraph break)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def normalize_text(raw: str) -> NormalizedText:
    """
    Full normalization pipeline for a raw OCR text string.

    Steps:
      1. Unicode NFKC normalization (compatibility decomposition).
      2. Remove zero-width / invisible control characters.
      3. Fix common OCR character-level errors.
      4. Standardize whitespace.

    Returns a NormalizedText with the original, cleaned text, and a log
    of issues that were detected and fixed.
    """
    if not raw or not raw.strip():
        return NormalizedText(original=raw, cleaned="", issues_found=["empty input"])

    issues: list[str] = []

    # Step 1: Unicode normalization
    text = unicodedata.normalize("NFKC", raw)
    if text != raw:
        issues.append("unicode NFKC normalization applied")

    # Step 2: Strip invisible characters
    stripped = _STRIP_CHARS.sub("", text)
    if stripped != text:
        issues.append("invisible characters removed")
    text = stripped

    # Step 3: OCR error fixes
    text, ocr_issues = fix_common_ocr_errors(text)
    issues.extend(ocr_issues)

    # Step 4: Whitespace standardization
    text = standardize_whitespace(text)

    return NormalizedText(original=raw, cleaned=text, issues_found=issues)
