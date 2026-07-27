"""
scripts/test_cleaning_pipeline.py

End-to-end test: Real PDF/Image -> OCR -> Cleaning -> Side-by-side comparison.

What this does:
    1. Accepts a PDF or image file as input (from command line or prompted)
    2. Converts PDF pages to images (via pdf2image / poppler)
    3. Runs each page through the full OCR pipeline (preprocess -> Vision API -> segment)
    4. Pipes every SegmentedAnswer.raw_text through normalize_text() + split_into_segments()
    5. Prints a detailed side-by-side report showing:
        - Raw OCR text (exactly what Vision API returned)
        - Cleaned text (after normalize_text)
        - Re-segmented breakdown (what split_into_segments found)
        - What changed (issues_found list)
    6. Saves a JSON report to data/samples/cleaning_report_<filename>.json

Usage:
    # With a PDF:
    uv run python scripts/test_cleaning_pipeline.py path/to/answer_sheet.pdf

    # With an image:
    uv run python scripts/test_cleaning_pipeline.py path/to/answer_sheet.png

    # Specify expected questions:
    uv run python scripts/test_cleaning_pipeline.py sheet.pdf --questions 1,2,3,4,5

    # Interactive prompt (no argument):
    uv run python scripts/test_cleaning_pipeline.py

Requirements:
    - For real OCR: GOOGLE_VISION_API_KEY in .env  (falls back to Mock if absent)
    - For PDF input: poppler installed (pdf2image dep)
        Windows:  scoop install poppler  OR  choco install poppler
                  OR download from https://github.com/oschwartz10612/poppler-windows/releases
    - uv sync --all-extras
"""

from __future__ import annotations

import json
import sys
import textwrap
from pathlib import Path
from typing import Any

# -- Ensure project root is importable when run directly ----------------------
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

# Force UTF-8 stdout on Windows so box characters print correctly
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    try:
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
    except Exception:
        pass


# =============================================================================
# Helpers
# =============================================================================


def _sep(char: str = "=", width: int = 72) -> str:
    return char * width


def _wrap(text: str, prefix: str = "|  ", width: int = 68) -> str:
    """Wrap long text lines and prefix each with a border marker."""
    if not text.strip():
        return f"{prefix}(empty)"
    lines = text.splitlines()
    wrapped_lines: list[str] = []
    for line in lines:
        if len(line) <= width:
            wrapped_lines.append(f"{prefix}{line}")
        else:
            for chunk in textwrap.wrap(line, width):
                wrapped_lines.append(f"{prefix}{chunk}")
    return "\n".join(wrapped_lines)


# =============================================================================
# PDF -> images
# =============================================================================


def pdf_to_images(pdf_path: Path) -> list[Path]:
    """
    Convert each PDF page to a PNG image using PyMuPDF (fitz).
    No poppler required -- pure Python wheel.
    Returns list of saved image paths in data/samples/.
    """
    try:
        import fitz  # PyMuPDF
    except ImportError:
        print("\nERROR: PyMuPDF is not installed. Run:  uv add pymupdf\n")
        sys.exit(1)

    output_dir = ROOT / "data" / "samples"
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = pdf_path.stem

    print(f"[PDF] Converting: {pdf_path.name} ...")

    try:
        doc = fitz.open(str(pdf_path))
    except Exception as exc:
        print(f"\nERROR: Could not open PDF: {exc}\n")
        sys.exit(1)

    saved: list[Path] = []
    # 200 DPI = zoom factor 200/72 ≈ 2.78
    zoom = 200 / 72
    mat = fitz.Matrix(zoom, zoom)

    for page_num in range(len(doc)):
        page = doc[page_num]
        pix = page.get_pixmap(matrix=mat, colorspace=fitz.csRGB)
        out_path = output_dir / f"{stem}_page_{page_num + 1}.png"
        pix.save(str(out_path))
        saved.append(out_path)
        print(f"  [OK] Page {page_num + 1} -> {out_path.name}  ({pix.width}x{pix.height}px)")

    doc.close()
    print(f"  [OK] {len(saved)} page(s) converted from PDF")
    return saved


# =============================================================================
# OCR client factory
# =============================================================================


def _build_ocr_client():
    from packages.common.config import get_settings
    from packages.ocr.vision_client import MockVisionClient

    settings = get_settings()

    if settings.google_vision_api_key:
        try:
            from packages.ocr.vision_client import GoogleVisionRestClient
            print(f"[KEY] Using Google Vision REST API (key: ...{settings.google_vision_api_key[-6:]})")
            return GoogleVisionRestClient(api_key=settings.google_vision_api_key)
        except Exception as e:
            print(f"[WARN] Google Vision init failed ({e}), falling back to Mock")

    if settings.google_application_credentials:
        try:
            from packages.ocr.vision_client import GoogleVisionSDKClient
            print("[KEY] Using Google Vision SDK (service account)")
            return GoogleVisionSDKClient()
        except Exception as e:
            print(f"[WARN] SDK client init failed ({e}), falling back to Mock")

    print("[WARN] No Google Vision credentials found -- using MockVisionClient")
    print("       Set GOOGLE_VISION_API_KEY in your .env file for real OCR results.")
    return MockVisionClient()


# =============================================================================
# Core pipeline per image
# =============================================================================


def run_pipeline_on_image(
    image_path: Path,
    page_num: int,
    question_numbers: list[int] | None,
    ocr_client,
) -> dict[str, Any]:
    """
    OCR -> normalize -> re-segment on a single image.
    Returns a structured result dict.
    """
    from packages.cleaning import normalize_text, split_into_segments
    from packages.ocr.pipeline import run_ocr_pipeline

    print(f"\n  [OCR] Running page {page_num}: {image_path.name} ...")

    segmented_answers = run_ocr_pipeline(
        image_path=image_path,
        question_numbers=question_numbers,
        ocr_client=ocr_client,
        page=page_num,
    )

    print(f"  [OK]  OCR done -- {len(segmented_answers)} question segment(s) detected")

    page_report: dict[str, Any] = {
        "page": page_num,
        "image_file": image_path.name,
        "ocr_segments_count": len(segmented_answers),
        "questions": [],
    }

    if not segmented_answers:
        print("  [!]  No question labels detected on this page.")
        print("       Tip: pass --questions 1,2,3 to specify expected question numbers.")
        return page_report

    for seg in segmented_answers:
        raw = seg.raw_text
        normalized = normalize_text(raw)
        re_segments = split_into_segments(raw, expected_questions=question_numbers)

        q_report = {
            "question_number": seg.question_number,
            "page": seg.page,
            "label_detected": seg.label_detected,
            "ocr_confidence": round(seg.ocr_confidence, 4),
            "raw_text": raw,
            "cleaned_text": normalized.cleaned,
            "issues_found": normalized.issues_found,
            "re_segments": [
                {
                    "question_number": rs.question_number,
                    "cleaned_text": rs.cleaned_text,
                    "label_format": rs.label_format,
                }
                for rs in re_segments
            ],
        }
        page_report["questions"].append(q_report)

    return page_report


# =============================================================================
# Terminal report printer
# =============================================================================


def print_report(all_pages: list[dict[str, Any]], input_file: str) -> None:
    """Print a readable side-by-side comparison to the terminal."""
    total_q = sum(len(p["questions"]) for p in all_pages)

    print(f"\n\n{_sep()}")
    print(f"  CLEANING PIPELINE REPORT  --  {Path(input_file).name}")
    print(_sep())
    print(f"  Pages processed  : {len(all_pages)}")
    print(f"  Total Q segments : {total_q}")
    print(_sep())

    for page_data in all_pages:
        print(f"\n{_sep('-')}")
        print(f"  PAGE {page_data['page']}  --  {page_data['image_file']}")
        print(f"  OCR found {page_data['ocr_segments_count']} segment(s)")
        print(_sep('-'))

        if not page_data["questions"]:
            print("  [!] No questions detected on this page.\n")
            continue

        for q in page_data["questions"]:
            q_num = q["question_number"]
            conf  = q["ocr_confidence"]
            label_tag = "label-found" if q["label_detected"] else "INFERRED (no label)"
            issues = q["issues_found"]

            print(f"\n  +-- Q{q_num}  [{label_tag}]  OCR confidence: {conf:.1%}")

            # Raw OCR
            print(f"  |")
            print(f"  |  >> RAW OCR TEXT (what Vision API returned):")
            print(_wrap(q["raw_text"] or "(no text)", prefix="  |    "))

            # Cleaned
            print(f"  |")
            print(f"  |  >> CLEANED TEXT (after normalize_text):")
            print(_wrap(q["cleaned_text"] or "(empty after cleaning)", prefix="  |    "))

            # Diff / changes
            print(f"  |")
            if issues:
                print(f"  |  >> CHANGES MADE ({len(issues)}):")
                for issue in issues:
                    print(f"  |      - {issue}")
            else:
                print(f"  |  >> CHANGES MADE: none -- text was already clean")

            # Re-segmentation
            re_segs = q.get("re_segments", [])
            if len(re_segs) > 1:
                print(f"  |")
                print(f"  |  >> RE-SPLIT: cleaning found {len(re_segs)} sub-questions in this OCR block:")
                for rs in re_segs:
                    label_info = rs['label_format'] if rs['label_format'] else "no label"
                    print(f"  |      Q{rs['question_number']} [{label_info}]:")
                    print(_wrap(rs["cleaned_text"][:200], prefix="  |        "))
            elif len(re_segs) == 1 and re_segs[0]["question_number"] != q_num:
                print(f"  |")
                print(f"  |  [!] RE-SPLIT: block re-numbered as Q{re_segs[0]['question_number']}")

            print(f"  +--")

    print(f"\n{_sep()}")
    print("  INTERPRETATION GUIDE")
    print(_sep('-'))
    print("  label-found      -- question number was explicitly in the OCR text (reliable)")
    print("  INFERRED         -- number was guessed; the cleaning module saw no label")
    print("  OCR confidence   -- mean confidence from Vision API (1.0 = perfect)")
    print("  CHANGES MADE     -- fixes applied by normalize_text()")
    print("  RE-SPLIT         -- cleaning found extra Q boundaries inside one OCR segment")
    print()
    print("  KNOWN LIMITATIONS on real handwritten sheets:")
    print("  - Word fragments: 'membr ane' won't be merged (needs LLM post-processing)")
    print("  - Digit misreads: '5'/'S', '0'/'O', '1'/'l' -- only partially fixed")
    print("  - No question label: entire page collapses to Q1 (watch for INFERRED)")
    print("  - Answers crossing pages: will appear in separate page sections above")
    print(_sep())
    print()


# =============================================================================
# Main
# =============================================================================


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Run OCR + Cleaning pipeline on a real answer sheet PDF or image.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            Examples:
              uv run python scripts/test_cleaning_pipeline.py answer_sheet.pdf
              uv run python scripts/test_cleaning_pipeline.py sheet.png --questions 1,2,3,4,5
              uv run python scripts/test_cleaning_pipeline.py sheet.pdf --no-save
        """),
    )
    parser.add_argument(
        "input_file",
        nargs="?",
        help="Path to PDF or image file. If omitted, you will be prompted.",
    )
    parser.add_argument(
        "--questions", "-q",
        help="Comma-separated expected question numbers, e.g. 1,2,3,4,5",
        default=None,
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="Skip saving the JSON report to disk.",
    )
    args = parser.parse_args()

    # -- Resolve input file ---------------------------------------------------
    if args.input_file:
        input_path = Path(args.input_file)
    else:
        raw = input("\nEnter path to your PDF or image file: ").strip().strip('"').strip("'")
        input_path = Path(raw)

    if not input_path.exists():
        print(f"\nERROR: File not found: {input_path}")
        sys.exit(1)

    # -- Parse expected question numbers -------------------------------------
    question_numbers: list[int] | None = None
    if args.questions:
        try:
            question_numbers = [int(x.strip()) for x in args.questions.split(",")]
            print(f"[INFO] Expected questions: {question_numbers}")
        except ValueError:
            print("ERROR: --questions must be comma-separated integers, e.g. 1,2,3")
            sys.exit(1)
    else:
        raw_q = input(
            "Enter expected question numbers (e.g. 1,2,3) or press Enter to auto-detect: "
        ).strip()
        if raw_q:
            try:
                question_numbers = [int(x.strip()) for x in raw_q.split(",")]
            except ValueError:
                print("[WARN] Could not parse question numbers -- using auto-detect mode.")

    print(f"\n{_sep('-')}")
    print(f"  Input file : {input_path.resolve()}")
    print(f"  Type       : {input_path.suffix.lower()}")
    print(f"  Questions  : {question_numbers if question_numbers else 'auto-detect'}")
    print(_sep('-'))

    # -- Convert PDF -> images -----------------------------------------------
    if input_path.suffix.lower() == ".pdf":
        image_paths = pdf_to_images(input_path)
    else:
        image_paths = [input_path]

    # -- Build OCR client ----------------------------------------------------
    ocr_client = _build_ocr_client()

    # -- Run pipeline on each page -------------------------------------------
    all_pages: list[dict[str, Any]] = []
    for page_num, img_path in enumerate(image_paths, start=1):
        page_result = run_pipeline_on_image(
            image_path=img_path,
            page_num=page_num,
            question_numbers=question_numbers,
            ocr_client=ocr_client,
        )
        all_pages.append(page_result)

    # -- Print terminal report -----------------------------------------------
    print_report(all_pages, str(input_path))

    # -- Save JSON report ----------------------------------------------------
    if not args.no_save:
        report_dir = ROOT / "data" / "samples"
        report_dir.mkdir(parents=True, exist_ok=True)
        report_path = report_dir / f"cleaning_report_{input_path.stem}.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "input_file": str(input_path.resolve()),
                    "question_numbers_hint": question_numbers,
                    "pages": all_pages,
                },
                f,
                indent=2,
                ensure_ascii=False,
            )
        print(f"  [SAVED] JSON report -> {report_path}\n")


if __name__ == "__main__":
    main()
