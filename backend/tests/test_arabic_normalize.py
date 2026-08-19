"""Arabic normalisation.

The property that matters throughout: normalisation is for *matching* only, and
must never be what a reader is shown. These tests pin both halves of that — that
matching collapses orthographic variation, and that display does not.
"""

from __future__ import annotations

import pytest

from tafahhum.arabic.normalize import (
    NormalizedText,
    arabic_ratio,
    is_arabic_script,
    normalize_digits,
    normalize_for_display,
    normalize_for_matching,
    normalize_key,
    strip_diacritics,
)

# 2:255 as printed in the Uthmani script, with full diacritics and a waqf mark.
AYAT_AL_KURSI_OPENING = "ٱللَّهُ لَاۤ إِلَـٰهَ إِلَّا هُوَ ٱلۡحَیُّ ٱلۡقَیُّومُۚ"


class TestDiacritics:
    def test_strips_harakat_and_quranic_marks(self):
        # The tatweel in إِلَـٰهَ goes too: it is a justification glyph, not a mark.
        assert strip_diacritics(AYAT_AL_KURSI_OPENING) == "ٱلله لا إله إلا هو ٱلحی ٱلقیوم"

    def test_tatweel_is_removed(self):
        assert strip_diacritics("الرحمـــن") == "الرحمن"


class TestMatchingForm:
    def test_collapses_uthmani_orthography(self):
        assert normalize_for_matching(AYAT_AL_KURSI_OPENING) == "الله لا اله الا هو الحي القيوم"

    @pytest.mark.parametrize(
        "variant",
        ["إبراهيم", "ابراهيم", "أبراهيم", "آبراهيم", "ٱبراهيم"],
    )
    def test_all_alef_forms_converge(self, variant):
        assert normalize_for_matching(variant) == "ابراهيم"

    @pytest.mark.parametrize(
        ("written", "expected"),
        [
            ("مكة", "مكه"),        # ta marbuta -> ha
            ("موسى", "موسي"),      # alef maqsura -> ya
            ("مسئول", "مسيول"),    # ya with hamza -> ya
            ("مؤمن", "مومن"),      # waw with hamza -> waw
            ("کتاب", "كتاب"),      # Persian keheh -> Arabic kaf
        ],
    )
    def test_letter_variants_converge(self, written, expected):
        assert normalize_for_matching(written) == expected

    def test_arabic_indic_digits_become_ascii(self):
        assert normalize_digits("٢٥٥") == "255"
        assert normalize_digits("۲۵۵") == "255"   # extended (Urdu/Persian) forms

    def test_whitespace_is_collapsed(self):
        assert normalize_for_matching("  الله   أكبر  ") == "الله اكبر"


class TestDisplayForm:
    def test_display_preserves_diacritics(self):
        """The single most important guarantee in this module."""
        out = normalize_for_display(AYAT_AL_KURSI_OPENING)
        assert "َ" in out or "ُ" in out, "harakat must survive display normalisation"
        assert "ٱ" in out, "alef wasla must survive display normalisation"

    def test_display_removes_bidi_controls(self):
        assert normalize_for_display("الله‏‎") == "الله"

    def test_display_and_matching_differ_on_vocalised_text(self):
        n = NormalizedText.of(AYAT_AL_KURSI_OPENING)
        assert n.display != n.matching
        assert n.original == AYAT_AL_KURSI_OPENING


class TestKeyForm:
    def test_key_drops_punctuation(self):
        assert normalize_key("البقرة، ٢٥٥") == normalize_key("البقرة 255")

    def test_key_lowercases_latin(self):
        assert normalize_key("Al-Baqarah") == normalize_key("al baqarah")


class TestScriptDetection:
    @pytest.mark.parametrize(
        ("text", "expected"),
        [("الله", True), ("hello", False), ("2:255", False), ("اردو", True)],
    )
    def test_is_arabic_script(self, text, expected):
        assert is_arabic_script(text) is expected

    def test_fully_arabic_text_scores_one(self):
        """Tatweel must not drag the ratio below 1.0 (it is a justification glyph)."""
        assert arabic_ratio("الرحمـــن") == 1.0
        assert arabic_ratio(AYAT_AL_KURSI_OPENING) == 1.0

    def test_latin_scores_zero(self):
        assert arabic_ratio("hello world") == 0.0

    def test_no_letters_scores_zero(self):
        assert arabic_ratio("2:255") == 0.0
