"""Carrying a query into the pivot language.

The corpus is Arabic. A query in English or Urdu cannot be matched against it
directly, so it is carried into Arabic before retrieval and the presentation
layer carries the result back. Arabic is the pivot rather than English because
the alternative — translating a million passages of classical Tafsir into English
and retrieving over that — would put a machine translation between the reader and
every source, which is precisely what this system exists to avoid.

Two things are being translated, and they have different requirements:

  the *query*     — needs to produce good retrieval terms. Precision of wording
                    matters less than hitting the vocabulary the corpus uses.
  the *passages*  — needs to be faithful, and is always shown beside the Arabic,
                    labelled, never substituted for it.

This module handles the first. Passage translation is a separate, slower,
attributed path (see `passage_translation` in the schema).

The default translator is a domain lexicon rather than a general model. For query
terms that is often the better tool: "occasion of revelation" must become
"سبب النزول", the technical term the corpus actually uses, and a general
translator will frequently produce a literal rendering that appears nowhere in
classical Tafsir. A model-backed translator implements the same protocol and
plugs in without touching anything downstream.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Protocol

from tafahhum.arabic.normalize import is_arabic_script, normalize_for_matching
from tafahhum.core.enums import PIVOT_LANGUAGE, Language


@dataclass(frozen=True)
class PivotResult:
    original: str
    pivot_text: str
    source_language: Language
    method: str
    #: Terms that were carried across, for the transparency panel.
    mapped_terms: tuple[tuple[str, str], ...] = ()
    note: str | None = None


class Translator(Protocol):
    """Anything that can carry text into the pivot language."""

    name: str

    def to_pivot(self, text: str, source: Language) -> PivotResult: ...


# ---------------------------------------------------------------------------
# Domain lexicon
#
# Terms are the technical vocabulary of Tafsir, mapped to the Arabic form the
# corpus actually uses. Multi-word entries are matched before single words so
# that "occasion of revelation" is not consumed as "revelation".
# ---------------------------------------------------------------------------

_EN_TO_AR: dict[str, str] = {
    # Core discipline
    "occasion of revelation": "سبب النزول",
    "occasions of revelation": "أسباب النزول",
    "reason for revelation": "سبب النزول",
    "abrogation": "النسخ",
    "abrogated": "منسوخ",
    "commentary": "تفسير",
    "tafsir": "تفسير",
    "tafseer": "تفسير",
    "tafasir": "تفسير",
    "tafaseer": "تفسير",
    "mufassir": "المفسر",
    "mufassirun": "المفسرون",
    "commentators": "المفسرون",
    "exegetes": "المفسرون",
    "scholars": "العلماء",
    "interpretation": "تأويل",
    "exegesis": "تفسير",
    "variant reading": "قراءة",
    "variant readings": "القراءات",
    "recitation": "قراءة",
    "chain of narration": "إسناد",
    "narration": "رواية",
    "tradition": "حديث",
    "hadith": "حديث",
    "companion": "صحابي",
    "companions": "الصحابة",
    "successor": "تابعي",
    "successors": "التابعون",
    "consensus": "إجماع",
    "legal ruling": "حكم",
    "ruling": "حكم",
    "rulings": "الأحكام",
    "jurisprudence": "الفقه",
    "creed": "العقيدة",
    "theology": "الكلام",
    "grammar": "النحو",
    "syntax": "الإعراب",
    "rhetoric": "البلاغة",
    "morphology": "الصرف",
    "meaning": "معنى",
    "meanings": "معاني",
    "word": "لفظ",
    "verse": "آية",
    "verses": "آيات",
    "chapter": "سورة",
    # Frequent theological vocabulary
    "monotheism": "التوحيد",
    "oneness of god": "التوحيد",
    "divine attributes": "الصفات",
    "attributes of god": "صفات الله",
    "sovereignty": "الملك",
    "dominion": "الملك",
    "throne": "الكرسي",
    "intercession": "الشفاعة",
    "forgiveness": "المغفرة",
    "mercy": "الرحمة",
    "repentance": "التوبة",
    "punishment": "العذاب",
    "reward": "الثواب",
    "paradise": "الجنة",
    "hellfire": "النار",
    "resurrection": "البعث",
    "judgement": "الحساب",
    "prophet": "النبي",
    "messenger": "الرسول",
    "revelation": "الوحي",
    "guidance": "الهداية",
    "disbelief": "الكفر",
    "faith": "الإيمان",
    "worship": "العبادة",
    "prayer": "الصلاة",
    "knowledge": "العلم",
    "life": "الحياة",
    "living": "الحي",
    "eternal": "القيوم",
    "sleep": "النوم",
    "slumber": "سنة",
    "heavens": "السماوات",
    "earth": "الأرض",
    "compulsion": "إكراه",
    "religion": "الدين",
}

_UR_TO_AR: dict[str, str] = {
    "شان نزول": "سبب النزول",
    "سبب نزول": "سبب النزول",
    "تفسیر": "تفسير",
    "معنی": "معنى",
    "مطلب": "معنى",
    "آیت": "آية",
    "آیات": "آيات",
    "سورہ": "سورة",
    "حدیث": "حديث",
    "روایت": "رواية",
    "صحابہ": "الصحابة",
    "قراءت": "القراءات",
    "احکام": "الأحكام",
    "فقہ": "الفقه",
    "عقیدہ": "العقيدة",
    "نحو": "النحو",
    "اعراب": "الإعراب",
    "بلاغت": "البلاغة",
    "توحید": "التوحيد",
    "شفاعت": "الشفاعة",
    "مغفرت": "المغفرة",
    "رحمت": "الرحمة",
    "توبہ": "التوبة",
    "عذاب": "العذاب",
    "جنت": "الجنة",
    "دوزخ": "النار",
    "قیامت": "البعث",
    "نبی": "النبي",
    "رسول": "الرسول",
    "وحی": "الوحي",
    "ہدایت": "الهداية",
    "کفر": "الكفر",
    "ایمان": "الإيمان",
    "عبادت": "العبادة",
    "نماز": "الصلاة",
    "علم": "العلم",
    "زندگی": "الحياة",
    "آسمان": "السماوات",
    "زمین": "الأرض",
    "دین": "الدين",
    "اختلاف": "اختلاف",
    "کرسی": "الكرسي",
}

# Words that carry no retrieval value and are dropped rather than mapped.
_EN_STOPWORDS = {
    "what", "who", "when", "where", "why", "how", "do", "does", "did", "the",
    "a", "an", "of", "on", "in", "to", "for", "about", "is", "are", "was",
    "were", "say", "says", "said", "tell", "me", "please", "and", "or", "this",
    "that", "these", "those", "it", "its", "according", "explain", "mean",
    "means", "give", "show", "there", "their", "them", "with", "from", "by",
    "at", "as", "be", "been", "have", "has", "had", "can", "could", "would",
}


def _extract_arabic_fragments(text: str) -> list[str]:
    """Arabic-script runs inside an otherwise non-Arabic query.

    A quoted Arabic phrase in an English question is the single strongest
    retrieval signal available, so it is preserved verbatim.
    """
    return [m.group(0).strip() for m in re.finditer(r"[؀-ۿ\s]{3,}", text) if m.group(0).strip()]


class LexiconTranslator:
    """Deterministic, offline term mapping into Arabic."""

    name = "tafahhum-lexicon-v1"

    def to_pivot(self, text: str, source: Language) -> PivotResult:
        if source is PIVOT_LANGUAGE:
            return PivotResult(
                original=text,
                pivot_text=text,
                source_language=source,
                method="passthrough",
            )

        lexicon = _UR_TO_AR if source is Language.UR else _EN_TO_AR
        mapped: list[tuple[str, str]] = []

        # Any Arabic already present in the query is kept as-is.
        pieces: list[str] = _extract_arabic_fragments(text)

        haystack = text.lower() if source is Language.EN else normalize_for_matching(text)
        consumed = haystack

        # Longest phrases first, so multi-word technical terms win.
        for term in sorted(lexicon, key=len, reverse=True):
            needle = term if source is Language.EN else normalize_for_matching(term)
            if needle and needle in consumed:
                arabic = lexicon[term]
                if arabic not in pieces:
                    pieces.append(arabic)
                mapped.append((term, arabic))
                consumed = consumed.replace(needle, " ")

        pivot_text = " ".join(pieces).strip()

        note = None
        if not pivot_text:
            note = (
                "No Arabic search terms could be derived from this query, so "
                "retrieval used the structural ayah match only. Searching in "
                "Arabic, or naming the concept in Arabic, will retrieve more."
            )
        elif source is not PIVOT_LANGUAGE:
            note = (
                f"Query terms were mapped into Arabic for retrieval "
                f"({self.name}). Source passages are shown in Arabic, untranslated."
            )

        return PivotResult(
            original=text,
            pivot_text=pivot_text,
            source_language=source,
            method="lexicon",
            mapped_terms=tuple(mapped),
            note=note,
        )


_default_translator: Translator = LexiconTranslator()


def set_translator(translator: Translator) -> None:
    """Install a different translator (e.g. a model-backed one)."""
    global _default_translator
    _default_translator = translator


def get_translator() -> Translator:
    return _default_translator


def to_pivot(text: str, source: Language | None = None) -> PivotResult:
    """Carry `text` into the pivot language."""
    if source is None:
        from tafahhum.language.detect import detect_language

        source = detect_language(text).language

    # Arabic-script input is already usable, whatever its language: an Urdu query
    # still contains Arabic technical vocabulary the index can match.
    if source is PIVOT_LANGUAGE or (source is Language.UR and is_arabic_script(text)):
        result = _default_translator.to_pivot(text, source)
        if source is PIVOT_LANGUAGE:
            return result
        # For Urdu, combine the mapped Arabic terms with the original script.
        combined = " ".join(filter(None, [result.pivot_text, text])).strip()
        return PivotResult(
            original=text,
            pivot_text=combined,
            source_language=source,
            method="lexicon+script",
            mapped_terms=result.mapped_terms,
            note=result.note,
        )

    return _default_translator.to_pivot(text, source)
