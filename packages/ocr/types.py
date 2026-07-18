"""
packages/ocr/types.py

Internal dataclasses for the OCR pipeline.
These types flow between preprocess → vision_client → segment → pipeline.
They are NOT Pydantic models and NOT ORM models — just lightweight Python dataclasses.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# ── Image preprocessing ───────────────────────────────────────────────────────


@dataclass
class PreprocessedImage:
    """
    Result of running an image through the preprocessing stage.

    Attributes:
        image:          The processed numpy array (uint8, grayscale or BGR).
        original_shape: (height, width[, channels]) of the raw input image.
        rotation_deg:   Degrees the image was rotated during deskew (0 if none).
        quality_score:  Heuristic 0-1 sharpness/contrast score for the page.
        source_path:    Absolute path of the file that was preprocessed.
    """

    image: Any  # np.ndarray — typed as Any to avoid a hard numpy import at module level
    original_shape: tuple[int, ...]
    rotation_deg: float = 0.0
    quality_score: float = 1.0
    source_path: str = ""


# ── OCR output ────────────────────────────────────────────────────────────────


@dataclass
class BoundingPoly:
    """
    Axis-aligned bounding rectangle for an OCR text block, in pixel space.
    Matches the subset of geometry returned by Google Vision.
    """

    x: int = 0
    y: int = 0
    width: int = 0
    height: int = 0
    page: int = 1

    def to_dict(self) -> dict[str, int]:
        return {
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "page": self.page,
        }

    @classmethod
    def from_dict(cls, d: dict[str, int]) -> BoundingPoly:
        return cls(
            x=d.get("x", 0),
            y=d.get("y", 0),
            width=d.get("width", 0),
            height=d.get("height", 0),
            page=d.get("page", 1),
        )


@dataclass
class OCRBlock:
    """
    A single text block returned by the Vision API (or mock).

    Attributes:
        text:       Raw text content of this block.
        confidence: Vision API word-level confidence (0.0 – 1.0).
        bounds:     Bounding rectangle in pixel space.
        page:       1-indexed page number this block came from.
    """

    text: str
    confidence: float = 1.0
    bounds: BoundingPoly = field(default_factory=BoundingPoly)
    page: int = 1


@dataclass
class OCRResult:
    """
    Full output from the Vision API for one page image.

    Attributes:
        blocks:       Ordered list of OCR text blocks (top-to-bottom, left-to-right).
        full_text:    Concatenated text of all blocks (convenience field).
        raw_response: The complete JSON-serialisable Vision API response dict.
                      Stored verbatim in `sheet_pages.ocr_raw_json`.
        page:         1-indexed page number this result belongs to.
    """

    blocks: list[OCRBlock] = field(default_factory=list)
    full_text: str = ""
    raw_response: dict[str, Any] = field(default_factory=dict)
    page: int = 1


# ── Segmentation output ───────────────────────────────────────────────────────


@dataclass
class SegmentedAnswer:
    """
    All OCR text attributed to a single question number.

    Attributes:
        question_number:    The detected (or inferred) question number.
        raw_text:           Merged text from all blocks for this question.
        bounding_boxes:     List of BoundingPoly dicts covering all contributing blocks.
        ocr_confidence:     Mean confidence across all contributing blocks.
        page:               Page number of the first block for this question.
        label_detected:     True if the question label was explicitly found in OCR text.
    """

    question_number: int
    raw_text: str
    bounding_boxes: list[dict[str, int]] = field(default_factory=list)
    ocr_confidence: float = 1.0
    page: int = 1
    label_detected: bool = True
