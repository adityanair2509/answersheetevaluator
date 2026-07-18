"""
packages/ocr/preprocess.py

OpenCV-based image preprocessing for scanned answer sheets.

Pipeline (in order):
    load_image → deskew_image → remove_noise → binarize → crop_borders
    → preprocess_sheet (runs all of the above)

All functions operate on numpy arrays (uint8).
Requires: opencv-python, numpy (both in the [ocr] extras group).
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

from packages.ocr.types import PreprocessedImage

# ---------------------------------------------------------------------------
# Lazy imports so the module can be imported even when opencv is not installed
# (unit tests that don't call cv2 functions will still pass).
# ---------------------------------------------------------------------------


def _cv2():  # type: ignore[return]
    try:
        import cv2  # type: ignore[import]

        return cv2
    except ImportError as exc:
        raise ImportError(
            "opencv-python is required for OCR preprocessing. Install it with: uv sync --all-extras"
        ) from exc


def _np():  # type: ignore[return]
    try:
        import numpy as np  # type: ignore[import]

        return np
    except ImportError as exc:
        raise ImportError(
            "numpy is required for OCR preprocessing. Install it with: uv sync --all-extras"
        ) from exc


# ── Public helpers ────────────────────────────────────────────────────────────


def load_image(path: str | Path) -> Any:  # returns np.ndarray
    """
    Load an image from disk as a BGR numpy array.

    Raises:
        FileNotFoundError: if the file does not exist.
        ValueError:        if cv2.imread returns None (unsupported format).
    """
    cv2 = _cv2()
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Image file not found: {path}")

    image = cv2.imread(str(path))
    if image is None:
        raise ValueError(
            f"cv2.imread returned None for '{path}'. "
            "The file may be corrupted or in an unsupported format."
        )
    return image


def to_grayscale(image: Any) -> Any:  # np.ndarray → np.ndarray
    """Convert BGR image to grayscale. Returns the image unchanged if already single-channel."""
    cv2 = _cv2()
    if len(image.shape) == 2:
        return image
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)


def deskew_image(image: Any) -> tuple[Any, float]:
    """
    Detect and correct page rotation using Hough-line analysis.

    Returns:
        (deskewed_image, rotation_degrees) — rotation_degrees is 0.0 if no
        significant skew was found (< 0.5°) or if the image is very small.
    """
    cv2 = _cv2()
    np = _np()

    gray = to_grayscale(image)
    h, w = gray.shape[:2]
    if h < 50 or w < 50:
        return image, 0.0

    # Edge detection on a downscaled version for speed
    scale = min(1.0, 1000 / max(h, w))
    small = cv2.resize(gray, (int(w * scale), int(h * scale)))
    blurred = cv2.GaussianBlur(small, (5, 5), 0)
    edges = cv2.Canny(blurred, 50, 150, apertureSize=3)

    lines = cv2.HoughLines(edges, 1, np.pi / 180, threshold=max(30, int(small.shape[1] * 0.3)))
    if lines is None:
        return image, 0.0

    angles: list[float] = []
    for line in lines[:20]:  # use up to 20 dominant lines
        rho, theta = line[0]
        # Convert theta to degrees offset from horizontal
        angle = math.degrees(theta) - 90
        if abs(angle) < 45:  # ignore near-vertical lines
            angles.append(angle)

    if not angles:
        return image, 0.0

    median_angle = float(np.median(angles))
    if abs(median_angle) < 0.5:
        return image, 0.0  # negligible skew — skip rotation

    # Rotate the original (full-resolution) image
    centre = (w // 2, h // 2)
    matrix = cv2.getRotationMatrix2D(centre, median_angle, 1.0)
    rotated = cv2.warpAffine(
        image,
        matrix,
        (w, h),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_REPLICATE,
    )
    return rotated, round(median_angle, 2)


def remove_noise(image: Any) -> Any:
    """
    Apply a mild bilateral filter to reduce scan noise while preserving edges.
    Works on both grayscale and BGR images.
    """
    cv2 = _cv2()
    if len(image.shape) == 2:
        return cv2.bilateralFilter(image, d=9, sigmaColor=75, sigmaSpace=75)
    return cv2.bilateralFilter(image, d=9, sigmaColor=75, sigmaSpace=75)


def binarize(image: Any) -> Any:
    """
    Convert to grayscale then apply adaptive Gaussian thresholding
    to produce a clean black-on-white binary image.
    This improves OCR accuracy on varying illumination.
    """
    cv2 = _cv2()
    gray = to_grayscale(image)
    # Adaptive threshold: block size 31, constant 10
    binary = cv2.adaptiveThreshold(
        gray,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        blockSize=31,
        C=10,
    )
    return binary


def crop_borders(image: Any, min_margin: int = 5) -> Any:
    """
    Remove white/empty borders from a binarized image.

    Finds the bounding rectangle of non-white content and crops to it,
    leaving at least `min_margin` pixels of padding on each side.
    Returns the original if no content is found or the image is already tight.
    """
    cv2 = _cv2()

    gray = to_grayscale(image)
    # Invert so white background becomes 0, content becomes 255
    inverted = cv2.bitwise_not(gray)
    coords = cv2.findNonZero(inverted)
    if coords is None:
        return image

    x, y, w, h = cv2.boundingRect(coords)
    img_h, img_w = image.shape[:2]

    x1 = max(0, x - min_margin)
    y1 = max(0, y - min_margin)
    x2 = min(img_w, x + w + min_margin)
    y2 = min(img_h, y + h + min_margin)

    cropped = image[y1:y2, x1:x2]
    # Don't crop if the result is too small (likely a bad threshold)
    if cropped.shape[0] < 20 or cropped.shape[1] < 20:
        return image
    return cropped


def _quality_score(image: Any) -> float:
    """
    Heuristic 0-1 quality score based on Laplacian variance (sharpness).
    Score of 1.0 means sharp; below 0.3 means probably blurry or empty.
    """
    cv2 = _cv2()
    np = _np()
    gray = to_grayscale(image)
    lap_var = cv2.Laplacian(gray, cv2.CV_64F).var()
    # Empirically: variance ~500+ = sharp scan, ~50 = blurry
    score = float(np.clip(lap_var / 500.0, 0.0, 1.0))
    return round(score, 4)


# ── Main entry point ──────────────────────────────────────────────────────────


def preprocess_sheet(image_path: str | Path) -> PreprocessedImage:
    """
    Full preprocessing pipeline for one answer-sheet page image.

    Steps:
        1. Load image from disk
        2. Deskew (detect and correct rotation)
        3. Remove noise (bilateral filter)
        4. Binarize (adaptive threshold)
        5. Crop borders (remove empty margin)
        6. Compute quality score

    Returns:
        PreprocessedImage with the processed array and metadata.

    Raises:
        FileNotFoundError: if the file does not exist.
        ValueError:        if the image cannot be decoded.
    """
    image = load_image(image_path)
    original_shape = image.shape

    image, rotation_deg = deskew_image(image)
    image = remove_noise(image)
    image = binarize(image)
    image = crop_borders(image)
    quality = _quality_score(image)

    return PreprocessedImage(
        image=image,
        original_shape=original_shape,
        rotation_deg=rotation_deg,
        quality_score=quality,
        source_path=str(image_path),
    )


def preprocess_from_array(image: Any, source_path: str = "") -> PreprocessedImage:
    """
    Run the preprocessing pipeline on an in-memory numpy array
    (useful for tests and for images loaded from PDF pages).

    Skips the load step; all other steps are identical to `preprocess_sheet`.
    """
    original_shape = image.shape
    image, rotation_deg = deskew_image(image)
    image = remove_noise(image)
    image = binarize(image)
    image = crop_borders(image)
    quality = _quality_score(image)

    return PreprocessedImage(
        image=image,
        original_shape=original_shape,
        rotation_deg=rotation_deg,
        quality_score=quality,
        source_path=source_path,
    )
