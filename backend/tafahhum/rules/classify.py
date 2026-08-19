"""Query classification.

Classification decides which retrieval strategy runs and which rules apply, so it
happens before retrieval and is recorded in the audit log. It is keyword- and
signal-based rather than model-based for three reasons: it must be deterministic
so a logged query run can be reproduced exactly, it must work identically in
Arabic, English, and Urdu, and its failure mode must be legible — a
misclassification should be traceable to a specific term, not to a model.

Signals beat keywords where they conflict. A resolved ayah reference plus two
named Mufassirun is a comparative query regardless of how it is phrased.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from tafahhum.arabic.normalize import normalize_key
from tafahhum.core.enums import QueryType
from tafahhum.quran.reference import AyahRef, parse_ayah_references

# Keyword sets per query type, in all three languages. Arabic and Urdu terms are
# stored normalised, because the query is normalised before matching.
_KEYWORDS: dict[QueryType, set[str]] = {
    QueryType.COMPARATIVE: {
        "compare", "comparison", "versus", "difference between", "differ",
        "قارن", "مقارنه", "الفرق بين", "بين",
        "موازنه", "فرق", "تقابل",
    },
    QueryType.ASBAB_AL_NUZUL: {
        "occasion of revelation", "reason for revelation", "why was revealed",
        "asbab al nuzul", "sabab",
        "سبب النزول", "اسباب النزول", "نزلت في",
        "شان نزول", "سبب نزول",
    },
    QueryType.QIRAAT: {
        "recitation", "qiraat", "qira'at", "variant reading", "readings",
        "قراءات", "القراءات", "قراءه", "الرسم",
        "قرات",
    },
    QueryType.FIQH: {
        "ruling", "legal", "permissible", "forbidden", "obligation", "fiqh",
        "احكام", "حكم", "الفقه", "فقهي", "حلال", "حرام", "واجب",
        "مسيله", "شرعي",
    },
    QueryType.AQEEDAH: {
        "creed", "belief", "theology", "attributes of god", "aqeedah",
        "العقيده", "عقيده", "الصفات", "التوحيد", "الايمان",
        "عقايد",
    },
    QueryType.HADITH: {
        "hadith", "narration", "reported", "isnad", "chain",
        "حديث", "الحديث", "روايه", "اسناد", "روي",
    },
    QueryType.LINGUISTIC: {
        "grammar", "syntax", "morphology", "irab", "i'rab", "rhetorical",
        "balagha", "linguistic",
        "اعراب", "نحو", "صرف", "البلاغه", "لغه", "لغوي",
        "قواعد", "گرامر",
    },
    QueryType.WORD_MEANING: {
        "meaning of the word", "what does the word", "definition of",
        "معني كلمه", "معني لفظ", "دلاله",
        "لفظ كا مطلب", "معني",
    },
    QueryType.HISTORICAL: {
        "develop", "development", "over time", "through history", "historically",
        "evolution", "chronological",
        "تطور", "عبر التاريخ", "تاريخيا", "تاريخ",
        "تاريخي", "ارتقا",
    },
    QueryType.SCHOLARLY_DISAGREEMENT: {
        "disagree", "disagreement", "dispute", "controversy", "differing opinions",
        "اختلاف", "خلاف", "اراء مختلفه", "تنازع",
        "اختلافات",
    },
    QueryType.MUFASSIR_BIOGRAPHY: {
        "who was", "biography", "born", "died", "life of", "when did he live",
        "من هو", "ترجمه", "سيره", "ولد", "توفي", "وفاته",
        "كون تهے", "سوانح",
    },
    QueryType.THEMATIC: {
        "theme", "topic", "concept", "throughout the quran", "in the quran",
        "موضوع", "مفهوم", "في القران",
        "موضوعي",
    },
    QueryType.SOURCE_SEARCH: {
        "which book", "what source", "find the passage", "where does",
        "اي كتاب", "المصدر", "اين ذكر",
    },
}

# Terms that mark a request for Tafsir of a specific ayah.
_TAFSIR_TERMS = {
    "tafsir", "tafseer", "commentary", "explain", "explanation", "interpret",
    "interpretation", "meaning", "say about",
    "تفسير", "معني", "شرح", "بيان", "تاويل",
    "مطلب", "وضاحت",
}


@dataclass
class Classification:
    query_type: QueryType
    confidence: float
    refs: list[AyahRef] = field(default_factory=list)
    matched_terms: list[str] = field(default_factory=list)
    named_works: list[str] = field(default_factory=list)
    residual_text: str = ""
    reason: str = ""

    @property
    def is_ayah_scoped(self) -> bool:
        return bool(self.refs)


def _match_keywords(normalized: str, raw_lower: str) -> dict[QueryType, list[str]]:
    hits: dict[QueryType, list[str]] = {}
    for qtype, terms in _KEYWORDS.items():
        for term in terms:
            haystack = normalized if not term.isascii() else raw_lower
            if term in haystack:
                hits.setdefault(qtype, []).append(term)
    return hits


def classify(
    text: str,
    *,
    known_work_terms: dict[str, str] | None = None,
) -> Classification:
    """Classify a query.

    `known_work_terms` maps a searchable name fragment to a work slug, so that
    naming Mufassirun is detected against the actual corpus rather than a
    hardcoded list. It is supplied by the caller from the database.
    """
    parsed = parse_ayah_references(text)
    normalized = normalize_key(text)
    raw_lower = text.lower()

    named_works: list[str] = []
    if known_work_terms:
        for fragment, slug in known_work_terms.items():
            if not fragment:
                continue
            haystack = normalized if not fragment.isascii() else raw_lower
            if fragment in haystack and slug not in named_works:
                named_works.append(slug)

    hits = _match_keywords(normalized, raw_lower)

    # --- signal-driven decisions, which override keyword counts --------------

    # Two or more named works is a comparison whatever the phrasing.
    if len(named_works) >= 2:
        return Classification(
            QueryType.COMPARATIVE, 0.95, parsed.refs,
            matched_terms=sorted({t for ts in hits.values() for t in ts}),
            named_works=named_works, residual_text=parsed.residual_text,
            reason=f"{len(named_works)} works named",
        )

    if QueryType.COMPARATIVE in hits:
        return Classification(
            QueryType.COMPARATIVE, 0.85, parsed.refs, hits[QueryType.COMPARATIVE],
            named_works, parsed.residual_text, "comparative keyword",
        )

    # A single named work with no ayah is a question about that work or author.
    if len(named_works) == 1 and not parsed.refs:
        qtype = (
            QueryType.MUFASSIR_BIOGRAPHY
            if QueryType.MUFASSIR_BIOGRAPHY in hits
            else QueryType.TAFSIR_SPECIFIC
        )
        return Classification(
            qtype, 0.8, parsed.refs, hits.get(qtype, []), named_works,
            parsed.residual_text, "single work named, no ayah",
        )

    # --- keyword-driven decisions -------------------------------------------

    # Specific topical types outrank the generic ayah-tafsir default, because a
    # question about legal rulings on an ayah needs different sources than a
    # question about its grammar, even though both name the same ayah.
    priority = [
        QueryType.ASBAB_AL_NUZUL,
        QueryType.QIRAAT,
        QueryType.SCHOLARLY_DISAGREEMENT,
        QueryType.HISTORICAL,
        QueryType.FIQH,
        QueryType.AQEEDAH,
        QueryType.LINGUISTIC,
        QueryType.HADITH,
        QueryType.MUFASSIR_BIOGRAPHY,
        QueryType.WORD_MEANING,
        QueryType.SOURCE_SEARCH,
    ]
    for qtype in priority:
        if qtype in hits:
            return Classification(
                qtype, 0.75, parsed.refs, hits[qtype], named_works,
                parsed.residual_text, f"keyword: {hits[qtype][0]}",
            )

    if len(named_works) == 1:
        return Classification(
            QueryType.MUFASSIR_SPECIFIC, 0.75, parsed.refs, [], named_works,
            parsed.residual_text, "one work named alongside an ayah",
        )

    if parsed.refs:
        asks_tafsir = any(
            (t in normalized if not t.isascii() else t in raw_lower)
            for t in _TAFSIR_TERMS
        )
        return Classification(
            QueryType.AYAH_TAFSIR,
            0.9 if asks_tafsir else 0.7,
            parsed.refs, [], named_works, parsed.residual_text,
            "ayah resolved" + (" with tafsir term" if asks_tafsir else ""),
        )

    if QueryType.THEMATIC in hits or len(re.findall(r"\w+", text)) > 2:
        return Classification(
            QueryType.THEMATIC, 0.5, [], hits.get(QueryType.THEMATIC, []),
            named_works, parsed.residual_text, "no ayah resolved; topical query",
        )

    return Classification(
        QueryType.UNKNOWN, 0.2, [], [], named_works, parsed.residual_text,
        "no classifying signal",
    )
