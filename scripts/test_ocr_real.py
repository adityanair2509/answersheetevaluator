"""
scripts/test_ocr_real.py

Real-world OCR test using the Google Vision REST API.

What this does:
    1. Generates a synthetic handwritten-style answer-sheet PNG using Pillow
    2. Saves it to data/samples/sample_answer_sheet.png
    3. Runs the full OCR pipeline against the Google Vision REST API
    4. Prints every detected SegmentedAnswer with its confidence score

Usage:
    uv run python scripts/test_ocr_real.py

Requirements:
    - GOOGLE_VISION_API_KEY must be set in your .env file
    - uv sync --all-extras (to have opencv-python + Pillow installed)
"""
from __future__ import annotations

import sys
from pathlib import Path

# Ensure project root is on sys.path when run directly
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))


# ─── 1. Render a synthetic answer-sheet image ─────────────────────────────────

def create_sample_answer_sheet(output_path: Path) -> Path:
    """
    Draw a realistic-looking A4 answer-sheet image with 3 questions
    using Pillow (no real handwriting — uses a clean monospace font).
    Returns the saved path.
    """
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print("ERROR: Pillow not installed. Run:  uv sync --all-extras")
        sys.exit(1)

    W, H = 794, 1123          # A4 @ 96 dpi
    img = Image.new("RGB", (W, H), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    # Try to load a system font; fall back gracefully
    try:
        font_header = ImageFont.truetype("arial.ttf", 22)
        font_body   = ImageFont.truetype("arial.ttf", 18)
    except OSError:
        font_header = ImageFont.load_default()
        font_body   = font_header

    # Page header
    draw.text((W // 2 - 180, 30), "CS301 — Mid-Term Examination 2024", font=font_header, fill=(0, 0, 0))
    draw.text((W // 2 - 80, 58), "Answer Sheet", font=font_body, fill=(0, 0, 0))
    draw.line([(40, 80), (W - 40, 80)], fill=(0, 0, 0), width=2)

    # Student info
    draw.text((50, 95),  "Name:  Aditya Nair",        font=font_body, fill=(0, 0, 0))
    draw.text((50, 118), "Roll No:  2021CS042",        font=font_body, fill=(0, 0, 0))
    draw.text((50, 141), "Section:  A",                font=font_body, fill=(0, 0, 0))
    draw.line([(40, 165), (W - 40, 165)], fill=(180, 180, 180), width=1)

    # Question 1
    draw.text((50, 185), "1. Define the concept of Big-O notation.", font=font_header, fill=(20, 20, 20))
    answer_q1 = [
        "Big-O notation is a mathematical notation used to describe the",
        "upper bound of an algorithm's time or space complexity in the",
        "worst case. It expresses how the runtime grows relative to the",
        "input size n. For example, O(n log n) means the runtime grows",
        "proportionally to n times the logarithm of n, which is typical",
        "for efficient sorting algorithms like merge sort and heap sort.",
    ]
    for i, line in enumerate(answer_q1):
        draw.text((70, 215 + i * 24), line, font=font_body, fill=(40, 40, 40))

    draw.line([(40, 375), (W - 40, 375)], fill=(200, 200, 200), width=1)

    # Question 2
    draw.text((50, 390), "2. Explain the difference between stack and queue.", font=font_header, fill=(20, 20, 20))
    answer_q2 = [
        "A stack is a LIFO (Last In First Out) data structure where the",
        "last element inserted is the first to be removed. Operations:",
        "push (insert) and pop (remove from top).",
        "",
        "A queue is a FIFO (First In First Out) data structure where the",
        "first element inserted is the first to be removed. Operations:",
        "enqueue (insert at rear) and dequeue (remove from front).",
        "",
        "Key difference: stacks use one end for both operations;",
        "queues use two ends (front and rear).",
    ]
    for i, line in enumerate(answer_q2):
        if line:
            draw.text((70, 422 + i * 24), line, font=font_body, fill=(40, 40, 40))

    draw.line([(40, 685), (W - 40, 685)], fill=(200, 200, 200), width=1)

    # Question 3
    draw.text((50, 700), "Q3) What is recursion? Give one example.", font=font_header, fill=(20, 20, 20))
    answer_q3 = [
        "Recursion is a programming technique where a function calls",
        "itself directly or indirectly to solve a problem. Each recursive",
        "call works on a smaller sub-problem until a base case is reached.",
        "",
        "Example: Factorial of n",
        "   factorial(n) = 1             if n == 0   (base case)",
        "   factorial(n) = n * factorial(n-1)        (recursive case)",
        "",
        "factorial(5) = 5 * 4 * 3 * 2 * 1 = 120",
    ]
    for i, line in enumerate(answer_q3):
        if line:
            draw.text((70, 732 + i * 24), line, font=font_body, fill=(40, 40, 40))

    # Footer
    draw.line([(40, H - 50), (W - 40, H - 50)], fill=(0, 0, 0), width=1)
    draw.text((50, H - 38), "Page 1 of 1", font=font_body, fill=(100, 100, 100))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(output_path), "PNG", dpi=(150, 150))
    print(f"✅  Sample answer sheet saved → {output_path}")
    return output_path


# ─── 2. Run the real OCR pipeline ────────────────────────────────────────────

def main() -> None:
    from packages.common.config import get_settings
    from packages.ocr.pipeline import run_ocr_pipeline
    from packages.ocr.vision_client import GoogleVisionRestClient, MockVisionClient, get_ocr_client

    settings = get_settings()

    # ── Generate sample image ──────────────────────────────────────────────────
    sample_path = Path("data/samples/sample_answer_sheet.png")
    create_sample_answer_sheet(sample_path)

    # ── Select OCR client ──────────────────────────────────────────────────────
    if settings.google_vision_api_key:
        print(f"\n🔑  Using Google Vision REST API  (key: ...{settings.google_vision_api_key[-6:]})")
        client = GoogleVisionRestClient(api_key=settings.google_vision_api_key)
    else:
        print("\n⚠️   GOOGLE_VISION_API_KEY not found in .env — using MockVisionClient instead")
        client = MockVisionClient()

    # ── Run pipeline ───────────────────────────────────────────────────────────
    print("\n⏳  Running OCR pipeline …")
    question_numbers = [1, 2, 3]
    answers = run_ocr_pipeline(
        image_path=sample_path,
        question_numbers=question_numbers,
        ocr_client=client,
        page=1,
    )

    # ── Print results ──────────────────────────────────────────────────────────
    print(f"\n{'=' * 70}")
    print(f"📄  OCR Results  —  {len(answers)} question(s) detected")
    print(f"{'=' * 70}\n")

    if not answers:
        print("❌  No answers detected. Check that question labels (1., 2., Q3) are present.")
        return

    for ans in answers:
        label_tag = "✅ label found" if ans.label_detected else "⚠️  inferred"
        print(f"┌─ Q{ans.question_number}  [{label_tag}]  confidence={ans.ocr_confidence:.2%}  page={ans.page}")
        for line in ans.raw_text.strip().splitlines():
            if line.strip():
                print(f"│  {line}")
        print(f"└─ bounding boxes: {len(ans.bounding_boxes)}")
        print()

    print(f"{'=' * 70}")
    print(f"✅  Done.  Total questions extracted: {len(answers)}")
    print(f"{'=' * 70}")

    # ── Commands used summary ─────────────────────────────────────────────────
    print("""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Commands used for testing this project:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  # 1. Run unit tests (fast, no API calls)
  uv run pytest tests/unit/ -q --tb=short

  # 2. Run unit tests verbosely (see each test name)
  uv run pytest tests/unit/ -v --tb=short

  # 3. Run THIS real OCR script (uses Vision API)
  uv run python scripts/test_ocr_real.py

  # 4. Verify OCR package imports cleanly
  uv run python -c "from packages.ocr import run_ocr_pipeline; print('OK')"

  # 5. Lint check (ruff)
  uv run ruff check packages/ocr/ tests/unit/

  # 6. Auto-fix lint issues
  uv run ruff check --fix packages/ocr/ tests/unit/

  # 7. Run full test suite with coverage
  uv run pytest tests/ -q --tb=short --cov=apps --cov=packages

  # 8. Start the FastAPI dev server
  .venv\\Scripts\\uvicorn apps.api.main:app --reload --host 0.0.0.0 --port 8000

  # 9. Check server health
  curl http://localhost:8000/health

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""")


if __name__ == "__main__":
    main()
