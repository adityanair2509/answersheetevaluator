"""
tests/unit/test_preprocess.py

Unit tests for packages/ocr/preprocess.py.

These tests use synthetic numpy arrays generated in-memory — no real images
on disk, no Google Vision calls, no camera required.
opencv-python must be installed (it is in the [ocr] extras group).
"""

from __future__ import annotations

import pytest

# ── Test 1: load_image raises FileNotFoundError for missing path ──────────────


def test_load_image_not_found() -> None:
    """load_image() must raise FileNotFoundError for a non-existent path."""
    from packages.ocr.preprocess import load_image

    with pytest.raises(FileNotFoundError, match="not found"):
        load_image("/this/path/does/not/exist.png")


# ── Test 2: binarize output has same spatial dimensions as input ──────────────


def test_binarize_output_shape() -> None:
    """
    binarize() must return a 2-D (grayscale) array with the same H×W
    as the input, regardless of whether the input is grayscale or BGR.
    """
    import numpy as np

    from packages.ocr.preprocess import binarize

    # Grayscale input
    gray = np.full((200, 300), 200, dtype=np.uint8)
    result = binarize(gray)
    assert result.shape == (200, 300), f"Expected (200, 300), got {result.shape}"
    assert result.dtype == np.uint8

    # BGR colour input (3 channels)
    bgr = np.full((150, 250, 3), 180, dtype=np.uint8)
    result_bgr = binarize(bgr)
    assert result_bgr.shape == (150, 250), f"Expected (150, 250), got {result_bgr.shape}"


# ── Test 3: preprocess_from_array returns a PreprocessedImage ────────────────


def test_preprocess_returns_dataclass() -> None:
    """
    preprocess_from_array() on a synthetic white image must return a
    PreprocessedImage with the correct original_shape and a quality_score
    in [0, 1].
    """
    import numpy as np

    from packages.ocr.preprocess import preprocess_from_array
    from packages.ocr.types import PreprocessedImage

    # Create a simple 400×600 grayscale image (white page)
    synthetic = np.full((400, 600), 255, dtype=np.uint8)

    result = preprocess_from_array(synthetic, source_path="synthetic_test")

    assert isinstance(result, PreprocessedImage), f"Expected PreprocessedImage, got {type(result)}"
    assert result.original_shape == (400, 600), f"original_shape mismatch: {result.original_shape}"
    assert 0.0 <= result.quality_score <= 1.0, f"quality_score out of range: {result.quality_score}"
    assert result.source_path == "synthetic_test"
    # Processed image must still be a 2D numpy array
    assert len(result.image.shape) == 2, "Processed image should be grayscale (2D)"
