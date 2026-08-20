"""Quranic reference parsing across Arabic, English, and Urdu."""

from __future__ import annotations

import pytest

from tafahhum.quran.reference import AyahRef, parse_ayah_references
from tafahhum.quran.surah_data import SURAH_BY_NUMBER, SURAHS, TOTAL_AYAHS


def refs(text: str) -> list[str]:
    return [str(r) for r in parse_ayah_references(text).refs]


class TestSurahTable:
    def test_has_all_surahs(self):
        assert len(SURAHS) == 114

    def test_total_ayah_count(self):
        """6236 is the ayah total of the Hafs an Asim reading."""
        assert TOTAL_AYAHS == 6236

    def test_al_baqarah_length(self):
        assert SURAH_BY_NUMBER[2].ayah_count == 286

    def test_numbering_is_contiguous(self):
        assert [s.number for s in SURAHS] == list(range(1, 115))


class TestNumericForms:
    @pytest.mark.parametrize(
        "text",
        ["2:255", "2.255", "2/255", "Q2:255", "q 2 : 255", "٢:٢٥٥", "۲:۲۵۵"],
    )
    def test_equivalent_numeric_spellings(self, text):
        assert refs(text) == ["2:255"]

    def test_range(self):
        assert refs("2:255-257") == ["2:255-257"]

    def test_en_dash_range(self):
        assert refs("2:255–257") == ["2:255-257"]

    def test_multiple_non_contiguous(self):
        assert refs("what about 2:255, 2:256 and 3:7") == ["2:255", "2:256", "3:7"]


class TestWordyForms:
    @pytest.mark.parametrize(
        "text",
        ["surah 2 ayah 255", "Surah 2, verse 255", "chapter 2 ayat 255"],
    )
    def test_english_wordy(self, text):
        assert refs(text) == ["2:255"]

    def test_arabic_wordy(self):
        assert refs("سورة البقرة الآية ٢٥٥") == ["2:255"]

    def test_urdu_wordy(self):
        """Urdu spells the words with heh goal and Persian yeh."""
        assert refs("سورہ بقرہ آیت ۲۵۵") == ["2:255"]


class TestNamedForms:
    def test_transliterated_name(self):
        assert refs("Al-Baqarah 255") == ["2:255"]

    @pytest.mark.parametrize(
        "spelling",
        ["Al-Baqarah 255", "al baqara 255", "Albaqarah 255", "Baqarah 255"],
    )
    def test_transliteration_variants(self, spelling):
        assert refs(spelling) == ["2:255"]

    def test_bare_arabic_name(self):
        assert refs("البقرة ٢٥٥") == ["2:255"]

    def test_named_range(self):
        assert refs("Surah Al-Kahf 10-12") == ["18:10-12"]

    @pytest.mark.parametrize(
        "text",
        ["tell me about Ayat al-Kursi", "آية الكرسي", "آیت الکرسی کی تفسیر"],
    )
    def test_alias_resolves(self, text):
        assert refs(text) == ["2:255"]


class TestValidation:
    def test_ayah_beyond_surah_length_is_rejected(self):
        """Al-Baqarah has 286 ayahs, so 2:300 is not a location."""
        assert refs("2:300") == []

    def test_surah_number_out_of_range_is_rejected(self):
        assert refs("115:1") == []

    def test_overrunning_range_is_truncated_to_surah_end(self):
        assert refs("2:280-999") == ["2:280-286"]

    def test_invalid_range_raises(self):
        with pytest.raises(ValueError):
            AyahRef(2, 255, 250)


class TestFalsePositives:
    """Ordinary prose containing numbers must not parse as references.

    Many surah names translate to common English nouns, so an unguarded
    name-plus-number rule turns "a man 5 times" into 76:5.
    """

    @pytest.mark.parametrize(
        "text",
        [
            "I met a man 5 times yesterday",
            "the light 3 was broken",
            "divine forgiveness in the Quran",
            "قال المفسرون 100 قول",
            "there are 114 surahs",
        ],
    )
    def test_no_spurious_match(self, text):
        assert refs(text) == []


class TestResidual:
    def test_reference_is_removed_from_residual(self):
        result = parse_ayah_references("what do the tafasir say about 2:255?")
        assert "2:255" not in result.residual_text
        assert "tafasir" in result.residual_text

    def test_residual_drives_semantic_search(self):
        result = parse_ayah_references("2:255 divine sovereignty")
        assert result.residual_text.strip() == "divine sovereignty"

    def test_empty_input(self):
        result = parse_ayah_references("")
        assert not result.has_reference


class TestLabels:
    def test_english_label(self):
        assert AyahRef(2, 255, 255).label("en") == "Al-Baqara 2:255"

    def test_range_label(self):
        assert AyahRef(2, 255, 257).label("en").endswith("2:255-257")

    def test_str_roundtrip(self):
        assert str(AyahRef(18, 10, 12)) == "18:10-12"
