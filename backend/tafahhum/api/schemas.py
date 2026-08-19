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


class PassageOut(BaseModel):
    passage_id: str
    text: str
    evidence_type: str
    verification_status: str
    ayah: str | None
    citation: CitationOut
    retrieval_strategies: list[str]
    fused_score: float


class WorkOut(BaseModel):
    work_slug: str
    title_ar: str
    title_en: str | None
    author_ar: str
    author_en: str | None
    author_death_year_hijri: int | None
    has_page_level_citation: bool
    passages: list[PassageOut]


class AyahOut(BaseModel):
    reference: str
    surah_number: int
    ayah_number: int
    surah_name_ar: str
    surah_name_en: str
    text_uthmani: str
    evidence_type: str = "QURANIC_TEXT"


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
    references: list[str]
    ayahs: list[AyahOut]
    works: list[WorkOut]
    passage_count: int
    page_level_citation_coverage: float
    notes: list[str]
    trace: TraceOut
    insufficient_evidence: bool


def serialise(package: EvidencePackage) -> QueryOut:
    return QueryOut(
        query=package.query,
        user_language=package.user_language.value,
        pivot_query=package.pivot_query,
        query_type=package.query_type.value,
        classification_confidence=package.classification_confidence,
        references=[str(r) for r in package.refs],
        ayahs=[
            AyahOut(
                reference=a.reference,
                surah_number=a.surah_number,
                ayah_number=a.ayah_number,
                surah_name_ar=a.surah_name_ar,
                surah_name_en=a.surah_name_en,
                text_uthmani=a.text_uthmani,
            )
            for a in package.ayah_texts
        ],
        works=[
            WorkOut(
                work_slug=w.work_slug,
                title_ar=w.work_title_ar,
                title_en=w.work_title_en,
                author_ar=w.author_name_ar,
                author_en=w.author_name_en,
                author_death_year_hijri=w.author_death_year_hijri,
                has_page_level_citation=w.has_page_level_citation,
                passages=[
                    PassageOut(
                        passage_id=p.passage_id,
                        text=p.display_text,
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
                            reference=p.citation.reference_string(
                                package.user_language.value
                            ),
                        ),
                        retrieval_strategies=p.strategies,
                        fused_score=round(p.fused_score, 6),
                    )
                    for p in w.passages
                ],
            )
            for w in package.works
        ],
        passage_count=package.passage_count,
        page_level_citation_coverage=round(package.page_level_citation_coverage, 4),
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
