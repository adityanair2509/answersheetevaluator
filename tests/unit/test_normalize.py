"""
tests/unit/test_normalize.py

Tests for the packages/cleaning module:
  - normalize.py  (OCR artifact fixing, whitespace, Unicode)
  - number_parser.py  (question label detection)
  - question_splitter.py  (text → per-question segments)
  - types.py  (dataclass construction)
"""

from __future__ import annotations

import pytest

from packages.cleaning import (
    NormalizedText,
    QuestionSegment,
    fix_common_ocr_errors,
    normalize_text,
    parse_question_label,
    split_into_segments,
    standardize_whitespace,
)


# ══════════════════════════════════════════════════════════════════════════════
# normalize.py
# ══════════════════════════════════════════════════════════════════════════════


class TestNormalizeText:
    """Tests for the full normalize_text pipeline."""

    def test_empty_string(self) -> None:
        result = normalize_text("")
        assert result.cleaned == ""
        assert "empty input" in result.issues_found

    def test_whitespace_only(self) -> None:
        result = normalize_text("   \n\n   ")
        assert result.cleaned == ""

    def test_clean_text_passes_through(self) -> None:
        text = "Photosynthesis is the process by which plants make food."
        result = normalize_text(text)
        assert result.cleaned == text
        assert result.original == text

    def test_unicode_nfkc(self) -> None:
        # NFKC converts ﬁ (U+FB01) → "fi"
        result = normalize_text("the ﬁrst step")
        assert "fi" in result.cleaned
        assert "unicode NFKC normalization applied" in result.issues_found

    def test_zero_width_chars_removed(self) -> None:
        text = "hello\u200bworld"  # zero-width space
        result = normalize_text(text)
        assert "\u200b" not in result.cleaned
        assert "invisible characters removed" in result.issues_found

    def test_preserves_original(self) -> None:
        raw = "  some   messy   text  \n\n\n\n"
        result = normalize_text(raw)
        assert result.original == raw
        assert result.cleaned != raw


class TestFixCommonOCRErrors:
    """Tests for OCR-specific character corrections."""

    def test_l_to_1_at_line_start(self) -> None:
        text, issues = fix_common_ocr_errors("l. Define osmosis.")
        assert text.startswith("1.")
        assert any("l→1" in i for i in issues)

    def test_pipe_to_1(self) -> None:
        text, issues = fix_common_ocr_errors("|2 is the answer")
        assert text.startswith("12")

    def test_O_to_0_between_digits(self) -> None:
        text, _ = fix_common_ocr_errors("1O0 grams")
        assert "100" in text

    def test_smart_quotes_normalized(self) -> None:
        text, _ = fix_common_ocr_errors("\u2018hello\u2019 \u201Cworld\u201D")
        assert "'" in text
        assert '"' in text

    def test_em_dash_normalized(self) -> None:
        text, _ = fix_common_ocr_errors("a\u2014b")
        assert "a-b" == text

    def test_clean_text_unchanged(self) -> None:
        original = "Normal text without OCR issues."
        text, issues = fix_common_ocr_errors(original)
        assert text == original
        assert issues == []


class TestStandardizeWhitespace:
    """Tests for whitespace normalization."""

    def test_collapse_multiple_spaces(self) -> None:
        assert standardize_whitespace("a   b   c") == "a b c"

    def test_collapse_tabs(self) -> None:
        assert standardize_whitespace("a\t\tb") == "a b"

    def test_preserve_single_newline(self) -> None:
        result = standardize_whitespace("line 1\nline 2")
        assert result == "line 1\nline 2"

    def test_collapse_excessive_newlines(self) -> None:
        result = standardize_whitespace("a\n\n\n\n\nb")
        assert result == "a\n\nb"

    def test_strip_trailing_spaces(self) -> None:
        result = standardize_whitespace("hello   \nworld   ")
        assert result == "hello\nworld"


# ══════════════════════════════════════════════════════════════════════════════
# number_parser.py
# ══════════════════════════════════════════════════════════════════════════════


class TestParseQuestionLabel:
    """Tests for question label extraction."""

    @pytest.mark.parametrize(
        "text,expected_num,expected_label",
        [
            ("1. Define osmosis.", 1, "1."),
            ("2) Explain photosynthesis.", 2, "2)"),
            ("3: List the steps.", 3, "3:"),
            ("(4) What is gravity?", 4, "(4)"),
            ("Q5 Newton's law", 5, "Q5"),
            ("Q.6 Describe the process.", 6, "Q.6"),
            ("Q7. Define momentum.", 7, "Q7."),
            ("Question 8 What is energy?", 8, "Question 8"),
            ("question 9) Water cycle", 9, "question 9)"),
            ("10. Multi-digit question.", 10, "10."),
        ],
    )
    def test_valid_labels(self, text: str, expected_num: int, expected_label: str) -> None:
        num, label = parse_question_label(text)
        assert num == expected_num
        assert label == expected_label

    def test_no_label_found(self) -> None:
        num, label = parse_question_label("The cell membrane is semi-permeable.")
        assert num is None
        assert label == ""

    def test_decimal_not_matched(self) -> None:
        # "2.4 mol/L" should NOT be detected as question 2
        num, _ = parse_question_label("The concentration is 2.4 mol/L.")
        assert num is None

    def test_mid_sentence_number_ignored(self) -> None:
        # Number deep in text should not match (prefix-only matching)
        num, _ = parse_question_label(
            "This is a long sentence that eventually mentions 5. somewhere."
        )
        assert num is None

    def test_leading_whitespace_handled(self) -> None:
        num, label = parse_question_label("   1. Define osmosis.")
        assert num == 1


# ══════════════════════════════════════════════════════════════════════════════
# question_splitter.py
# ══════════════════════════════════════════════════════════════════════════════


class TestSplitIntoSegments:
    """Tests for the text → per-question segment splitter."""

    SAMPLE_ANSWER_KEY = """\
1. Osmosis is the movement of water molecules through a selectively permeable
membrane from a region of lower solute concentration to a region of higher
solute concentration.

2. Photosynthesis is the process by which green plants use sunlight to
synthesize food from carbon dioxide and water.

3. Newton's first law states that an object at rest stays at rest, and an
object in motion stays in motion unless acted upon by an external force.
"""

    def test_basic_split(self) -> None:
        segments = split_into_segments(self.SAMPLE_ANSWER_KEY)
        assert len(segments) == 3
        assert segments[0].question_number == 1
        assert segments[1].question_number == 2
        assert segments[2].question_number == 3

    def test_segment_content(self) -> None:
        segments = split_into_segments(self.SAMPLE_ANSWER_KEY)
        # Q1 text should contain "Osmosis" but NOT the "1." label
        assert "Osmosis" in segments[0].cleaned_text
        assert not segments[0].cleaned_text.startswith("1.")

    def test_segment_label_format(self) -> None:
        segments = split_into_segments(self.SAMPLE_ANSWER_KEY)
        assert segments[0].label_format == "1."

    def test_empty_text(self) -> None:
        assert split_into_segments("") == []
        assert split_into_segments("   ") == []

    def test_no_labels_fallback(self) -> None:
        """If no question labels are found, return entire text as Q1."""
        text = "This is a free-form answer with no question numbers at all."
        segments = split_into_segments(text)
        assert len(segments) == 1
        assert segments[0].question_number == 1
        assert "free-form" in segments[0].cleaned_text

    def test_expected_questions_filter(self) -> None:
        """Only accept questions from the expected list."""
        text = "1. Answer one.\n2. Answer two.\n3. Answer three."
        segments = split_into_segments(text, expected_questions=[1, 3])
        numbers = [s.question_number for s in segments]
        assert 1 in numbers
        assert 3 in numbers
        # Q2 body should be absorbed into Q1 (the previous segment)
        assert 2 not in numbers

    def test_q_prefix_format(self) -> None:
        text = "Q1. Define osmosis.\nQ2. Explain photosynthesis."
        segments = split_into_segments(text)
        assert len(segments) == 2
        assert segments[0].question_number == 1
        assert segments[1].question_number == 2

    def test_cleaned_text_is_normalized(self) -> None:
        """Verify that cleaned_text has OCR fixes applied."""
        text = "1. The  ﬁrst   step   is  important."
        segments = split_into_segments(text)
        cleaned = segments[0].cleaned_text
        # NFKC should convert ﬁ → fi
        assert "fi" in cleaned
        # Multiple spaces should be collapsed
        assert "  " not in cleaned


# ══════════════════════════════════════════════════════════════════════════════
# types.py — basic construction tests
# ══════════════════════════════════════════════════════════════════════════════


class TestTypes:
    """Verify dataclass construction and defaults."""

    def test_normalized_text_defaults(self) -> None:
        nt = NormalizedText(original="raw", cleaned="clean")
        assert nt.issues_found == []

    def test_question_segment_defaults(self) -> None:
        qs = QuestionSegment(question_number=1, raw_text="raw", cleaned_text="clean")
        assert qs.label_format == ""
