"""
tests/unit/test_ocr_pipeline.py

Unit tests for the full OCR pipeline:
    MockVisionClient  →  segment.py  →  pipeline.py

No real images on disk and no Google Vision API calls are made.
All tests operate on in-memory numpy arrays or synthetic OCRBlock lists.
"""
from __future__ import annotations

import numpy as np
import pytest

from packages.ocr.segment import assign_blocks_to_questions, detect_question_number
from packages.ocr.types import BoundingPoly, OCRBlock, OCRResult
from packages.ocr.vision_client import MockVisionClient

# ── Helper ────────────────────────────────────────────────────────────────────


def _make_block(text: str, confidence: float = 0.9, page: int = 1) -> OCRBlock:
    """Construct a simple OCRBlock for testing."""
    return OCRBlock(
        text=text,
        confidence=confidence,
        bounds=BoundingPoly(x=0, y=0, width=100, height=30, page=page),
        page=page,
    )


def _synthetic_image(h: int = 300, w: int = 400) -> np.ndarray:
    """Create a synthetic grey numpy image for pipeline tests."""
    return np.full((h, w), 200, dtype=np.uint8)


# ── Test 1: MockVisionClient returns a valid OCRResult ───────────────────────


def test_mock_client_returns_ocr_result() -> None:
    """MockVisionClient.annotate() must return an OCRResult with blocks."""
    client = MockVisionClient()
    fake_bytes = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100  # fake PNG header bytes

    result = client.annotate(fake_bytes, page=1)

    assert isinstance(result, OCRResult), f"Expected OCRResult, got {type(result)}"
    assert len(result.blocks) > 0, "MockVisionClient must return at least one block"
    assert isinstance(result.full_text, str), "full_text must be a string"
    assert result.page == 1
    for block in result.blocks:
        assert isinstance(block, OCRBlock)
        assert 0.0 <= block.confidence <= 1.0, f"Block confidence out of range: {block.confidence}"


# ── Test 2: detect_question_number recognises all label patterns ──────────────


@pytest.mark.parametrize(
    "text, expected",
    [
        ("1. The process of photosynthesis …", 1),
        ("2) Newton's second law …", 2),
        ("Q3 The water cycle …", 3),
        ("Q.4 Explain osmosis …", 4),
        ("Question 5. Define entropy.", 5),
        ("10. Discuss the causes of the French Revolution.", 10),
        ("q12) Short answer here.", 12),
        # These should NOT be detected (number mid-sentence / missing label)
        ("stored in glucose molecules.", None),
        ("The concentration is 2.4 mol/L in the beaker.", None),
        ("", None),
        ("   ", None),
    ],
)
def test_segment_known_question_labels(text: str, expected: int | None) -> None:
    """detect_question_number must handle all supported label formats."""
    result = detect_question_number(text)
    assert result == expected, (
        f"For text {str(text)[:60]!r}: expected {expected}, got {result}"
    )


# ── Test 3: Full pipeline end-to-end with MockVisionClient ───────────────────


def test_pipeline_end_to_end_mock() -> None:
    """
    run_ocr_pipeline_from_array must return a non-empty list of SegmentedAnswers
    when given a synthetic image and the default MockVisionClient.
    The mock returns 3 question blocks (Q1, Q2, Q3) by default.
    """
    from packages.ocr.pipeline import run_ocr_pipeline_from_array
    from packages.ocr.types import SegmentedAnswer

    image = _synthetic_image()
    client = MockVisionClient()

    answers = run_ocr_pipeline_from_array(
        image,
        question_numbers=[1, 2, 3],
        ocr_client=client,
        page=1,
        source_path="test_synthetic",
    )

    assert len(answers) > 0, "Pipeline must produce at least one SegmentedAnswer"
    for ans in answers:
        assert isinstance(ans, SegmentedAnswer)
        assert ans.question_number >= 1
        assert isinstance(ans.raw_text, str)
        assert 0.0 <= ans.ocr_confidence <= 1.0
        assert ans.page == 1


# ── Test 4: Unlabelled blocks inherit the previous question's number ──────────


def test_missing_question_labels_inherited() -> None:
    """
    Blocks without a question label must be appended to the most recent
    labelled question rather than being lost.
    """
    blocks = [
        _make_block("1. First sentence of answer one."),
        _make_block("Continuation of answer one — no label here."),
        _make_block("Still part of answer one."),
        _make_block("2. Beginning of answer two."),
        _make_block("Second sentence of answer two."),
    ]

    answers = assign_blocks_to_questions(blocks, known_questions=[1, 2])

    assert len(answers) == 2, f"Expected 2 segments, got {len(answers)}"

    q1 = next(a for a in answers if a.question_number == 1)
    q2 = next(a for a in answers if a.question_number == 2)

    # Q1 should contain the two continuation blocks
    assert "Continuation" in q1.raw_text, (
        "Continuation block not merged into Q1"
    )
    assert "Still part" in q1.raw_text, (
        "Second continuation block not merged into Q1"
    )
    # Q2 should only contain its own blocks
    assert "Second sentence" in q2.raw_text


# ── Test 5: Confidence aggregation is mean of contributing blocks ─────────────


def test_confidence_aggregation() -> None:
    """
    SegmentedAnswer.ocr_confidence must equal the mean of all contributing
    OCRBlock confidences, rounded to 4 decimal places.
    """
    blocks = [
        _make_block("1. First block.", confidence=0.80),
        _make_block("Second block — continuation.", confidence=0.60),
        _make_block("Third block — continuation.", confidence=0.70),
    ]

    answers = assign_blocks_to_questions(blocks, known_questions=[1])

    assert len(answers) == 1
    q1 = answers[0]

    expected_conf = round((0.80 + 0.60 + 0.70) / 3, 4)
    assert abs(q1.ocr_confidence - expected_conf) < 1e-4, (
        f"Expected confidence {expected_conf}, got {q1.ocr_confidence}"
    )
