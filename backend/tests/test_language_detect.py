"""Language detection for the three user languages.

Arabic and Urdu share a script, so these tests concentrate on separating them.
"""

from __future__ import annotations

import pytest

from tafahhum.core.enums import PIVOT_LANGUAGE, USER_LANGUAGES, Language
from tafahhum.language.detect import detect_language


def lang(text: str) -> Language:
    return detect_language(text).language


class TestEnglish:
    @pytest.mark.parametrize(
        "text",
        [
            "What do the Tafasir say about 2:255?",
            "Compare Tabari, Qurtubi and Ibn Kathir",
            "who was al-Tabari",
        ],
    )
    def test_latin_is_english(self, text):
        assert lang(text) is Language.EN

    def test_english_with_quoted_arabic(self):
        """An Arabic phrase quoted inside an English question stays English."""
        assert lang("Compare Tabari and Qurtubi on الحي القيوم") is Language.EN


class TestArabic:
    @pytest.mark.parametrize(
        "text",
        [
            "ما معنى قوله تعالى الله لا اله الا هو الحي القيوم",
            "قارن بين الطبري والقرطبي وابن كثير",
            "من هو الإمام الطبري",
        ],
    )
    def test_arabic_detected(self, text):
        assert lang(text) is Language.AR


class TestUrdu:
    @pytest.mark.parametrize(
        "text",
        [
            "آیت الکرسی کی تفسیر کیا ہے؟",
            "اس آیت کے بارے میں مفسرین کیا کہتے ہیں",
            "طبری اور قرطبی کا موازنہ کریں",
        ],
    )
    def test_urdu_detected(self, text):
        """Urdu-specific letters are near-conclusive evidence."""
        assert lang(text) is Language.UR

    def test_urdu_marker_raises_confidence(self):
        weak = detect_language("تفسیر")
        strong = detect_language("اس آیت کے بارے میں مفسرین کیا کہتے ہیں")
        assert strong.confidence > weak.confidence


class TestEdgeCases:
    def test_empty_falls_back_to_default(self):
        assert detect_language("", default=Language.UR).language is Language.UR

    def test_bare_reference_has_no_language(self):
        """"2:255" is language-neutral; the caller's UI language decides."""
        result = detect_language("2:255", default=Language.AR)
        assert result.language is Language.AR
        assert result.confidence < 0.5

    def test_arabic_script_without_markers_defaults_to_arabic(self):
        """Safer than Urdu: the corpus is Arabic, so a misroute still retrieves."""
        assert lang("كتاب") is Language.AR

    def test_result_is_deterministic(self):
        """Classification is logged in the audit trail and must be reproducible."""
        text = "آیت الکرسی کی تفسیر"
        assert detect_language(text) == detect_language(text)


class TestConfiguration:
    def test_pivot_is_arabic(self):
        assert PIVOT_LANGUAGE is Language.AR

    def test_three_user_languages(self):
        assert set(USER_LANGUAGES) == {Language.AR, Language.EN, Language.UR}

    def test_rtl_flags(self):
        assert Language.AR.is_rtl and Language.UR.is_rtl
        assert not Language.EN.is_rtl
