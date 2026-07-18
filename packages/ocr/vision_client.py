"""
packages/ocr/vision_client.py

Google Vision API wrapper and mock fallback for development / testing.

Exports:
    GoogleVisionClient  — wraps google.cloud.vision.ImageAnnotatorClient
    MockVisionClient    — returns deterministic dummy blocks (no API call)
    get_ocr_client()    — factory: picks the right client based on settings
    run_ocr()           — top-level function: image → OCRResult
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any

import httpx

from packages.ocr.types import BoundingPoly, OCRBlock, OCRResult

logger = logging.getLogger(__name__)


# ── Abstract base ─────────────────────────────────────────────────────────────


class BaseOCRClient(ABC):
    """Common interface for all OCR backends."""

    @abstractmethod
    def annotate(self, image_bytes: bytes, page: int = 1) -> OCRResult:
        """
        Send raw image bytes to the OCR backend and return a structured result.

        Args:
            image_bytes: PNG/JPEG bytes of the image to annotate.
            page:        1-indexed page number to attach to all returned blocks.

        Returns:
            OCRResult with blocks, full_text, and the raw backend response.
        """


# ── Google Vision implementation ──────────────────────────────────────────────


class GoogleVisionClient(BaseOCRClient):
    """
    Wraps ``google.cloud.vision.ImageAnnotatorClient``.

    Credentials are resolved via the standard Google Cloud priority:
        1. GOOGLE_APPLICATION_CREDENTIALS env var (path to service-account JSON)
        2. Application Default Credentials (gcloud auth)

    The client is lazily created on the first call to ``annotate()`` so that
    importing this module does not fail when the google-cloud-vision package
    is not installed (non-OCR extras group).
    """

    def __init__(self, credentials_path: str | None = None) -> None:
        self._credentials_path = credentials_path
        self._client: Any = None  # google.cloud.vision.ImageAnnotatorClient

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        try:
            from google.cloud import vision  # type: ignore[import]
            from google.oauth2 import service_account  # type: ignore[import]
        except ImportError as exc:
            raise ImportError(
                "google-cloud-vision is required. Install it with: uv sync --all-extras"
            ) from exc

        if self._credentials_path:
            creds = service_account.Credentials.from_service_account_file(
                self._credentials_path,
                scopes=["https://www.googleapis.com/auth/cloud-vision"],
            )
            self._client = vision.ImageAnnotatorClient(credentials=creds)  # type: ignore[call-arg]
        else:
            # Application Default Credentials
            self._client = vision.ImageAnnotatorClient()
        return self._client

    def annotate(self, image_bytes: bytes, page: int = 1) -> OCRResult:
        from google.cloud import vision  # type: ignore[import]

        client = self._get_client()
        gv_image = vision.Image(content=image_bytes)
        response = client.document_text_detection(image=gv_image)

        if response.error.message:
            raise RuntimeError(f"Google Vision API error: {response.error.message}")

        blocks: list[OCRBlock] = []
        full_text = response.full_text_annotation.text if response.full_text_annotation else ""

        # Iterate over pages → blocks → paragraphs → words for confidence
        for page_ann in response.full_text_annotation.pages:
            for block_ann in page_ann.blocks:
                block_text_parts: list[str] = []
                word_confidences: list[float] = []

                for para in block_ann.paragraphs:
                    for word in para.words:
                        word_text = "".join(s.text for s in word.symbols)
                        block_text_parts.append(word_text)
                        word_confidences.append(word.confidence)

                if not block_text_parts:
                    continue

                bv = block_ann.bounding_box.vertices
                x_coords = [v.x for v in bv]
                y_coords = [v.y for v in bv]
                x, y = min(x_coords), min(y_coords)
                w = max(x_coords) - x
                h = max(y_coords) - y

                avg_conf = (
                    sum(word_confidences) / len(word_confidences) if word_confidences else 1.0
                )
                blocks.append(
                    OCRBlock(
                        text=" ".join(block_text_parts),
                        confidence=round(avg_conf, 4),
                        bounds=BoundingPoly(x=x, y=y, width=w, height=h, page=page),
                        page=page,
                    )
                )

        raw: dict[str, Any] = {}
        try:
            from google.protobuf.json_format import MessageToDict  # type: ignore[import]

            raw = MessageToDict(response._pb)
        except Exception:  # noqa: BLE001
            raw = {"error": "could not serialise response"}

        return OCRResult(blocks=blocks, full_text=full_text, raw_response=raw, page=page)


# ── Google Vision REST implementation (API key) ───────────────────────────────


class GoogleVisionRestClient(BaseOCRClient):
    """
    Calls the Google Cloud Vision API via its REST endpoint using an API key.
    Use this when you have an ``AIzaSy…`` key from the Cloud Console
    instead of a full service-account JSON file.

    Endpoint:
        POST https://vision.googleapis.com/v1/images:annotate?key=<API_KEY>

    Args:
        api_key: The ``AIzaSy…`` REST API key string.
    """

    _ENDPOINT = "https://vision.googleapis.com/v1/images:annotate"

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    def annotate(self, image_bytes: bytes, page: int = 1) -> OCRResult:
        import base64

        b64 = base64.b64encode(image_bytes).decode("utf-8")
        payload = {
            "requests": [
                {
                    "image": {"content": b64},
                    "features": [{"type": "DOCUMENT_TEXT_DETECTION"}],
                }
            ]
        }
        response = httpx.post(
            self._ENDPOINT,
            params={"key": self._api_key},
            json=payload,
            timeout=30.0,
        )
        if response.status_code != 200:
            raise RuntimeError(
                f"Google Vision REST API error {response.status_code}: {response.text[:300]}"
            )

        data = response.json()
        annotation = data.get("responses", [{}])[0]

        # Extract error if present
        if "error" in annotation:
            raise RuntimeError(f"Vision API error: {annotation['error'].get('message', 'unknown')}")

        full_text = annotation.get("fullTextAnnotation", {}).get("text", "")
        raw_pages = annotation.get("fullTextAnnotation", {}).get("pages", [])

        blocks: list[OCRBlock] = []
        for raw_page in raw_pages:
            for block in raw_page.get("blocks", []):
                words: list[str] = []
                word_confs: list[float] = []
                for para in block.get("paragraphs", []):
                    for word in para.get("words", []):
                        word_text = "".join(s.get("text", "") for s in word.get("symbols", []))
                        words.append(word_text)
                        word_confs.append(word.get("confidence", 1.0))

                if not words:
                    continue

                verts = block.get("boundingBox", {}).get("vertices", [])
                xs = [v.get("x", 0) for v in verts]
                ys = [v.get("y", 0) for v in verts]
                x, y = (min(xs), min(ys)) if xs and ys else (0, 0)
                w = (max(xs) - x) if xs else 0
                h = (max(ys) - y) if ys else 0

                avg_conf = sum(word_confs) / len(word_confs) if word_confs else 1.0
                blocks.append(
                    OCRBlock(
                        text=" ".join(words),
                        confidence=round(avg_conf, 4),
                        bounds=BoundingPoly(x=x, y=y, width=w, height=h, page=page),
                        page=page,
                    )
                )

        return OCRResult(
            blocks=blocks,
            full_text=full_text,
            raw_response=annotation,
            page=page,
        )


# Default blocks returned by the mock client — covers 3 questions with
# realistic text that the segmenter can parse.
_DEFAULT_MOCK_BLOCKS: list[dict[str, Any]] = [
    {
        "text": "1. The process of photosynthesis converts light energy into chemical energy.",
        "confidence": 0.92,
        "bounds": {"x": 50, "y": 80, "width": 500, "height": 30, "page": 1},
    },
    {
        "text": "stored in glucose molecules using CO2 and water.",
        "confidence": 0.88,
        "bounds": {"x": 50, "y": 115, "width": 480, "height": 28, "page": 1},
    },
    {
        "text": "2. Newton's second law states that F = ma, where F is the net force,",
        "confidence": 0.95,
        "bounds": {"x": 50, "y": 200, "width": 510, "height": 30, "page": 1},
    },
    {
        "text": "m is mass in kilograms, and a is acceleration in m/s^2.",
        "confidence": 0.93,
        "bounds": {"x": 50, "y": 235, "width": 490, "height": 28, "page": 1},
    },
    {
        "text": "Q3) The water cycle describes the continuous movement of water",
        "confidence": 0.90,
        "bounds": {"x": 50, "y": 320, "width": 505, "height": 30, "page": 1},
    },
    {
        "text": "through evaporation, condensation, and precipitation.",
        "confidence": 0.87,
        "bounds": {"x": 50, "y": 355, "width": 450, "height": 28, "page": 1},
    },
]


class MockVisionClient(BaseOCRClient):
    """
    Deterministic in-process mock — returns pre-configured OCR blocks
    without making any API calls.

    Use this in:
    - Unit tests
    - Development without a Google Cloud project
    - CI/CD pipelines where credentials are not available

    Args:
        blocks: Override the default mock blocks for custom test scenarios.
    """

    def __init__(self, blocks: list[dict[str, Any]] | None = None) -> None:
        self._blocks_spec = blocks or _DEFAULT_MOCK_BLOCKS

    def annotate(self, image_bytes: bytes, page: int = 1) -> OCRResult:  # noqa: ARG002
        blocks = [
            OCRBlock(
                text=b["text"],
                confidence=b.get("confidence", 1.0),
                bounds=BoundingPoly.from_dict({**b.get("bounds", {}), "page": page}),
                page=page,
            )
            for b in self._blocks_spec
        ]
        full_text = "\n".join(b.text for b in blocks)
        raw = {
            "mock": True,
            "blocks": [
                {"text": b["text"], "confidence": b.get("confidence", 1.0)}
                for b in self._blocks_spec
            ],
        }
        return OCRResult(blocks=blocks, full_text=full_text, raw_response=raw, page=page)


# ── Factory ───────────────────────────────────────────────────────────────────


def get_ocr_client(
    provider: str | None = None,
    credentials_path: str | None = None,
    api_key: str | None = None,
    force_mock: bool = False,
) -> BaseOCRClient:
    """
    Return the appropriate OCR client.

    Decision logic:
        1. If ``force_mock=True`` → always MockVisionClient
        2. If ``provider`` is ``'mock'`` → MockVisionClient
        3. If ``api_key`` (AIzaSy…) is provided → GoogleVisionRestClient
        4. If ``provider`` is ``'google_vision'`` and a service-account JSON
           exists at ``credentials_path`` → GoogleVisionClient
        5. Settings fallback: use ``GOOGLE_VISION_API_KEY`` from .env
        6. Credentials missing → warn and fall back to MockVisionClient

    Args:
        provider:         OCR backend name. Defaults to ``settings.ocr_provider``.
        credentials_path: Path to a service-account JSON key file.
        api_key:          REST API key (``AIzaSy…``). Overrides service-account.
        force_mock:       Skip all checks and return MockVisionClient directly.

    Returns:
        A fully initialised BaseOCRClient.
    """
    if force_mock:
        return MockVisionClient()

    # Resolve defaults from settings (avoid module-level import)
    if provider is None or credentials_path is None or api_key is None:
        from packages.common.config import get_settings

        s = get_settings()
        provider = provider or s.ocr_provider
        credentials_path = credentials_path or s.google_application_credentials
        api_key = api_key or s.google_vision_api_key

    if provider == "mock":
        return MockVisionClient()

    if provider == "google_vision":
        # Prefer REST API key if available
        if api_key:
            logger.info("Using GoogleVisionRestClient (API key auth)")
            return GoogleVisionRestClient(api_key=api_key)

        # Fall back to service-account JSON
        if credentials_path:
            import os

            if os.path.exists(credentials_path):
                logger.info("Using GoogleVisionClient (service-account auth)")
                return GoogleVisionClient(credentials_path=credentials_path)
            else:
                logger.warning(
                    "google_vision credentials file not found at '%s'. "
                    "Falling back to MockVisionClient.",
                    credentials_path,
                )
        else:
            logger.warning(
                "Neither GOOGLE_VISION_API_KEY nor GOOGLE_APPLICATION_CREDENTIALS set. "
                "Falling back to MockVisionClient."
            )
        return MockVisionClient()

    logger.warning("Unknown OCR provider '%s'. Falling back to MockVisionClient.", provider)
    return MockVisionClient()


# ── Top-level convenience function ────────────────────────────────────────────


def run_ocr(image: Any, client: BaseOCRClient, page: int = 1) -> OCRResult:
    """
    Encode a numpy image array to PNG bytes and call ``client.annotate()``.

    Args:
        image:  numpy ndarray (uint8, grayscale or BGR).
        client: Any BaseOCRClient instance.
        page:   1-indexed page number to attach to all returned blocks.

    Returns:
        OCRResult from the backend.

    Raises:
        ImportError: if cv2 is not installed.
        RuntimeError: if encoding fails.
    """
    try:
        import cv2  # type: ignore[import]
    except ImportError as exc:
        raise ImportError(
            "opencv-python is required for image encoding. Install it with: uv sync --all-extras"
        ) from exc

    success, encoded = cv2.imencode(".png", image)
    if not success:
        raise RuntimeError("cv2.imencode failed — could not encode image to PNG bytes.")

    image_bytes = encoded.tobytes()
    return client.annotate(image_bytes, page=page)
