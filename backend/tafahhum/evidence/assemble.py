"""Evidence assembly.

The evidence package is the boundary between retrieval and presentation. Anything
downstream — a generated answer, a rendered page, an export — is a function of
this object and nothing else. It carries its own citations, so no later stage
needs to look one up, and therefore no later stage is able to invent one.

Assembly deliberately does not rank interpretations, resolve disagreements, or
decide which Mufassir is correct. It groups, labels, and orders.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import psycopg

from tafahhum.core.enums import EvidenceType, Language, QueryType, VerificationStatus
from tafahhum.quran.reference import AyahRef
from tafahhum.retrieval.models import RetrievalTrace, RetrievedPassage
from tafahhum.rules.classify import Classification
from tafahhum.language.translate import Translation, fetch_many
from tafahhum.rules.engine import RetrievalPlan


@dataclass(frozen=True)
class AyahTranslation:
    """An established translation of an ayah, by a named translator.

    Revealed text is never machine-translated. A reader in English or Urdu is
    shown a recognised translation with its translator named, so they know whose
    rendering they are reading.
    """

    text: str
    language: Language
    translator_name: str
    translation_slug: str


@dataclass(frozen=True)
class AyahText:
    """The Quranic text under discussion, kept separate from all commentary."""

    surah_number: int
    ayah_number: int
    surah_name_ar: str
    surah_name_en: str
    text_uthmani: str
    translations: tuple[AyahTranslation, ...] = ()
    evidence_kind: EvidenceType = EvidenceType.QURANIC_TEXT

    @property
    def reference(self) -> str:
        return f"{self.surah_number}:{self.ayah_number}"


@dataclass
class WorkEvidence:
    """Everything retrieved from a single work, kept together."""

    work_slug: str
    work_title_ar: str
    work_title_en: str | None
    author_name_ar: str
    author_name_en: str | None
    author_death_year_hijri: int | None
    passages: list[RetrievedPassage] = field(default_factory=list)

    @property
    def has_page_level_citation(self) -> bool:
        return any(p.citation.resolves_to_page for p in self.passages)

    @property
    def verification_summary(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for p in self.passages:
            out[p.verification_status.value] = out.get(p.verification_status.value, 0) + 1
        return out


@dataclass
class EvidencePackage:
    """The sealed input to presentation and generation."""

    query: str
    user_language: Language
    pivot_query: str
    query_type: QueryType
    classification_confidence: float
    refs: list[AyahRef] = field(default_factory=list)
    ayah_texts: list[AyahText] = field(default_factory=list)
    works: list[WorkEvidence] = field(default_factory=list)
    trace: RetrievalTrace = field(default_factory=RetrievalTrace)
    rules_applied: list[dict[str, str]] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    #: Cached translations keyed by passage id, in the user's language. Absent
    #: entries mean no translation exists yet, not that none is possible.
    translations: dict[str, Translation] = field(default_factory=dict)

    @property
    def is_empty(self) -> bool:
        return not any(w.passages for w in self.works)

    @property
    def passage_count(self) -> int:
        return sum(len(w.passages) for w in self.works)

    @property
    def translation_coverage(self) -> float:
        """Fraction of retrieved passages that have a translation available."""
        total = self.passage_count
        if not total:
            return 0.0
        return len(self.translations) / total

    @property
    def citable_passage_ids(self) -> set[str]:
        """The only identifiers a generated answer may reference."""
        return {p.passage_id for w in self.works for p in w.passages}

    @property
    def page_level_citation_coverage(self) -> float:
        """Fraction of passages whose citation reaches an actual printed page."""
        total = self.passage_count
        if not total:
            return 0.0
        resolved = sum(
            1 for w in self.works for p in w.passages if p.citation.resolves_to_page
        )
        return resolved / total


def fetch_ayah_texts(
    conn: psycopg.Connection,
    refs: list[AyahRef],
    language: Language = Language.AR,
) -> list[AyahText]:
    """Load the Quranic text for the queried references, with translations."""
    if not refs:
        return []

    conditions, params = [], []
    for ref in refs:
        conditions.append("(a.surah_number = %s AND a.ayah_number BETWEEN %s AND %s)")
        params.extend([ref.surah, ref.start, ref.end])

    with conn.cursor() as cur:
        cur.execute(
            f"""
            SELECT a.surah_number, a.ayah_number, a.text_uthmani,
                   s.name_ar, s.name_en_translit
            FROM ayah a
            JOIN surah s ON s.number = a.surah_number
            JOIN quran_text_source q ON q.id = a.text_source_id
            WHERE q.is_default AND ({' OR '.join(conditions)})
            ORDER BY a.surah_number, a.ayah_number
            """,
            params,
        )
        rows = cur.fetchall()

    translations: dict[tuple[int, int], list[AyahTranslation]] = {}
    if language is not Language.AR:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT surah_number, ayah_number, text, translator_name,
                       translation_slug
                FROM ayah_translation
                WHERE language = %s AND ({' OR '.join(
                    '(surah_number = %s AND ayah_number BETWEEN %s AND %s)'
                    for _ in refs
                )})
                ORDER BY translation_slug
                """,
                [language.value, *params],
            )
            for r in cur.fetchall():
                translations.setdefault((r["surah_number"], r["ayah_number"]), []).append(
                    AyahTranslation(
                        text=r["text"],
                        language=language,
                        translator_name=r["translator_name"],
                        translation_slug=r["translation_slug"],
                    )
                )

    return [
        AyahText(
            surah_number=r["surah_number"],
            ayah_number=r["ayah_number"],
            surah_name_ar=r["name_ar"],
            surah_name_en=r["name_en_translit"],
            text_uthmani=r["text_uthmani"],
            translations=tuple(translations.get((r["surah_number"], r["ayah_number"]), [])),
        )
        for r in rows
    ]


def group_by_work(
    passages: list[RetrievedPassage], *, order_by_death_year: bool = False
) -> list[WorkEvidence]:
    """Group passages by their work, preserving retrieval order within each.

    When ordering chronologically, works whose author death year is unknown are
    placed after the dated ones rather than being assigned an implied position —
    an unknown date is a fact about the corpus, not a value to sort on.
    """
    grouped: dict[str, WorkEvidence] = {}
    for p in passages:
        c = p.citation
        entry = grouped.get(c.work_slug)
        if entry is None:
            entry = WorkEvidence(
                work_slug=c.work_slug,
                work_title_ar=c.work_title_ar,
                work_title_en=c.work_title_en,
                author_name_ar=c.author_name_ar,
                author_name_en=c.author_name_en,
                author_death_year_hijri=c.author_death_year_hijri,
            )
            grouped[c.work_slug] = entry
        entry.passages.append(p)

    works = list(grouped.values())
    if order_by_death_year:
        dated = [w for w in works if w.author_death_year_hijri is not None]
        undated = [w for w in works if w.author_death_year_hijri is None]
        dated.sort(key=lambda w: w.author_death_year_hijri or 0)
        return dated + undated
    return works


def assemble(
    conn: psycopg.Connection,
    *,
    query: str,
    user_language: Language,
    pivot_query: str,
    classification: Classification,
    plan: RetrievalPlan,
    passages: list[RetrievedPassage],
    trace: RetrievalTrace,
) -> EvidencePackage:
    """Build the evidence package."""
    works = group_by_work(passages, order_by_death_year=plan.order_by_death_year)

    package = EvidencePackage(
        query=query,
        user_language=user_language,
        pivot_query=pivot_query,
        query_type=classification.query_type,
        classification_confidence=classification.confidence,
        refs=classification.refs,
        ayah_texts=fetch_ayah_texts(conn, classification.refs, user_language),
        works=works,
        trace=trace,
        rules_applied=plan.explain(),
    )

    # Translations are looked up, never produced here: assembly must stay a
    # database read so that a query cannot silently become a paid model call.
    # Missing translations are requested explicitly by the caller.
    if user_language is not Language.AR:
        package.translations = fetch_many(
            conn, [p.passage_id for w in works for p in w.passages], user_language
        )

    # Notes are user-facing statements about the limits of this result set. They
    # exist so a limitation is disclosed rather than left for the reader to infer.
    if package.is_empty:
        package.notes.append(
            "Insufficient verified evidence was retrieved from the current corpus."
        )
    else:
        coverage = package.page_level_citation_coverage
        if coverage == 0.0:
            package.notes.append(
                "No passage in this result set carries a page-level citation: the "
                "editions indexed are digital texts with no identified print "
                "edition. Citations resolve to the work, not to a page."
            )
        elif coverage < 1.0:
            package.notes.append(
                f"{coverage:.0%} of retrieved passages carry a page-level citation."
            )

        unverified = sum(
            1
            for w in package.works
            for p in w.passages
            if p.verification_status is not VerificationStatus.VERIFIED
        )
        if unverified:
            package.notes.append(
                f"{unverified} of {package.passage_count} passages have not been "
                "verified against a page image by a human reviewer."
            )

    return package
