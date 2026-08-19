"""API response shapes.

The serialised evidence package is the API's contract. It is deliberately verbose
about provenance: a client should never have to make a second request to find out
where a passage came from, and should never be able to render a passage without
also having its citation in hand.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from tafahhum.core.enums import AnswerMode, Language
from tafahhum.evidence.assemble import EvidencePackage


class QueryIn(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    language: Language | None = Field(
        default=None,
        description="User language. Detected from the query when omitted.",
    )
    mode: AnswerMode = AnswerMode.DETAILED
    limit: int | None = Field(default=None, ge=1, le=100)
    works: list[str] | None = Field(
        default=None, description="Restrict retrieval to these work slugs."
    )


class CitationOut(BaseModel):
    passage_id: str
    work_slug: str
    work_title_ar: str
    work_title_en: str | None
    author_name_ar: str
    author_name_en: str | None
    author_death_year_hijri: int | None
    edition_slug: str
    volume: int | None
    page_start: int | None
    page_end: int | None
    scan_page_uri: str | None
    resolves_to_page: bool
    citation_precision: str
    reference: str


class PassageTranslationOut(BaseModel):
    """A translation of a passage. Always accompanies the original, never replaces it."""

    text: str
    language: str
    translator_kind: str
    translator_name: str
    model_name: str | None
    verification_status: str
    is_machine: bool


class PassageOut(BaseModel):
    passage_id: str
    #: The source text, always in the language the Mufassir wrote in.
    text: str
    text_language: str
    #: Rendering into the reader's language, when one exists. `null` means no
    #: translation is stored yet — not that the passage cannot be translated.
    translation: PassageTranslationOut | None
    evidence_type: str
    verification_status: str
    ayah: str | None
    citation: CitationOut
    retrieval_strategies: list[str]
    fused_score: float
    #: 1-based index into the response's `references` list.
    reference_number: int


class WorkOut(BaseModel):
    work_slug: str
    title_ar: str
    title_en: str | None
    author_ar: str
    author_en: str | None
    author_death_year_hijri: int | None
    has_page_level_citation: bool
    passages: list[PassageOut]


class AyahTranslationOut(BaseModel):
    text: str
    language: str
    translator_name: str
    translation_slug: str


class AyahOut(BaseModel):
    reference: str
    surah_number: int
    ayah_number: int
    surah_name_ar: str
    surah_name_en: str
    text_uthmani: str
    #: Established translations by named translators. Revealed text is never
    #: machine-translated.
    translations: list[AyahTranslationOut] = []
    evidence_type: str = "QURANIC_TEXT"


class ReferenceOut(BaseModel):
    """One numbered source in the reference list.

    Carries everything a reader needs to locate and judge the source without a
    second request: who wrote it, which edition was indexed, where that edition
    came from, what its licence status is, and how far a citation into it
    actually resolves.
    """

    number: int
    work_slug: str
    work_title_ar: str
    work_title_en: str | None
    author_name_ar: str
    author_name_en: str | None
    author_death_year_hijri: int | None
    author_dates_verified: bool
    edition_slug: str
    edition_publisher: str | None
    edition_year: int | None
    digital_source_url: str | None
    copyright_status: str
    license_note: str | None
    passages_cited: int
    resolves_to_page: bool
    citation_precision: str
    verification_status: str
    full_citation: str


class TraceOut(BaseModel):
    """The "how this answer was built" payload.

    System decisions and evidence only — never model reasoning.
    """

    strategies_run: list[str]
    candidates_per_strategy: dict[str, int]
    filters_applied: dict[str, object]
    fused_candidates: int
    returned: int
    works_represented: int
    rules_applied: list[dict[str, str]]


class QueryOut(BaseModel):
    query: str
    user_language: str
    pivot_query: str
    query_type: str
    classification_confidence: float
    #: Quranic locations resolved from the query, e.g. ["2:255"].
    ayah_references: list[str]
    ayahs: list[AyahOut]
    works: list[WorkOut]
    #: Every source consulted, numbered, with full provenance.
    references: list[ReferenceOut]
    passage_count: int
    page_level_citation_coverage: float
    translation_coverage: float
    untranslated_passage_ids: list[str]
    notes: list[str]
    trace: TraceOut
    insufficient_evidence: bool


def _build_references(package: EvidencePackage) -> list[ReferenceOut]:
    """Number every source consulted, in the order it appears in the results.

    The numbering is what lets a passage carry a compact marker while the full
    provenance lives in one place — the same contract as a footnote in a printed
    critical edition.
    """
    lang = package.user_language.value
    out: list[ReferenceOut] = []

    for index, work in enumerate(package.works, start=1):
        if not work.passages:
            continue
        first = work.passages[0].citation
        out.append(
            ReferenceOut(
                number=index,
                work_slug=work.work_slug,
                work_title_ar=work.work_title_ar,
                work_title_en=work.work_title_en,
                author_name_ar=work.author_name_ar,
                author_name_en=work.author_name_en,
                author_death_year_hijri=work.author_death_year_hijri,
                # Dates come from a bibliographical source, which has not been
                # ingested yet; a missing date is reported, never guessed.
                author_dates_verified=work.author_death_year_hijri is not None,
                edition_slug=first.edition_slug,
                edition_publisher=first.edition_publisher,
                edition_year=first.edition_year,
                digital_source_url=first.edition_source_url,
                copyright_status=first.edition_copyright_status,
                license_note=first.edition_license_note,
                passages_cited=len(work.passages),
                resolves_to_page=work.has_page_level_citation,
                citation_precision=first.citation_precision.value,
                verification_status=first.edition_verification_status.value,
                full_citation=first.reference_string(lang),
            )
        )
    return out


def serialise(package: EvidencePackage) -> QueryOut:
    references = _build_references(package)
    number_by_work = {r.work_slug: r.number for r in references}
    untranslated: list[str] = []

    # An Arabic reader already has the source. Listing its passages as
    # "untranslated" would send the client off to translate Arabic into Arabic.
    wants_translation = package.user_language is not Language.AR

    def passage_out(p) -> PassageOut:
        stored = package.translations.get(p.passage_id)
        if stored is None and wants_translation and p.language is not package.user_language:
            untranslated.append(p.passage_id)
        return PassageOut(
            passage_id=p.passage_id,
            text=p.display_text,
            text_language=p.language.value,
            translation=(
                PassageTranslationOut(
                    text=stored.text,
                    language=stored.language.value,
                    translator_kind=stored.translator_kind,
                    translator_name=stored.translator_name,
                    model_name=stored.model_name,
                    verification_status=stored.verification_status.value,
                    is_machine=stored.is_machine,
                )
                if stored is not None
                else None
            ),
            evidence_type=p.evidence_kind.value,
            verification_status=p.verification_status.value,
            ayah=p.ayah_label,
            citation=CitationOut(
                passage_id=p.citation.passage_id,
                work_slug=p.citation.work_slug,
                work_title_ar=p.citation.work_title_ar,
                work_title_en=p.citation.work_title_en,
                author_name_ar=p.citation.author_name_ar,
                author_name_en=p.citation.author_name_en,
                author_death_year_hijri=p.citation.author_death_year_hijri,
                edition_slug=p.citation.edition_slug,
                volume=p.citation.volume,
                page_start=p.citation.page_start,
                page_end=p.citation.page_end,
                scan_page_uri=p.citation.scan_page_uri,
                resolves_to_page=p.citation.resolves_to_page,
                citation_precision=p.citation.citation_precision.value,
                reference=p.citation.reference_string(package.user_language.value),
            ),
            retrieval_strategies=p.strategies,
            fused_score=round(p.fused_score, 6),
            reference_number=number_by_work.get(p.citation.work_slug, 0),
        )

    works = [
        WorkOut(
            work_slug=w.work_slug,
            title_ar=w.work_title_ar,
            title_en=w.work_title_en,
            author_ar=w.author_name_ar,
            author_en=w.author_name_en,
            author_death_year_hijri=w.author_death_year_hijri,
            has_page_level_citation=w.has_page_level_citation,
            passages=[passage_out(p) for p in w.passages],
        )
        for w in package.works
    ]

    return QueryOut(
        query=package.query,
        user_language=package.user_language.value,
        pivot_query=package.pivot_query,
        query_type=package.query_type.value,
        classification_confidence=package.classification_confidence,
        ayah_references=[str(r) for r in package.refs],
        ayahs=[
            AyahOut(
                reference=a.reference,
                surah_number=a.surah_number,
                ayah_number=a.ayah_number,
                surah_name_ar=a.surah_name_ar,
                surah_name_en=a.surah_name_en,
                text_uthmani=a.text_uthmani,
                translations=[
                    AyahTranslationOut(
                        text=t.text,
                        language=t.language.value,
                        translator_name=t.translator_name,
                        translation_slug=t.translation_slug,
                    )
                    for t in a.translations
                ],
            )
            for a in package.ayah_texts
        ],
        works=works,
        references=references,
        passage_count=package.passage_count,
        page_level_citation_coverage=round(package.page_level_citation_coverage, 4),
        translation_coverage=round(package.translation_coverage, 4),
        untranslated_passage_ids=untranslated,
        notes=package.notes,
        trace=TraceOut(
            strategies_run=package.trace.strategies_run,
            candidates_per_strategy=package.trace.candidates_per_strategy,
            filters_applied=package.trace.filters_applied,
            fused_candidates=package.trace.fused_candidates,
            returned=package.trace.returned,
            works_represented=package.trace.works_represented,
            rules_applied=package.rules_applied,
        ),
        insufficient_evidence=package.is_empty,
    )
