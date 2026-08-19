"""Retrieval result types.

A retrieved passage carries its provenance with it from the moment it leaves the
database. Nothing downstream has to look anything up to build a citation, which
is what makes it impossible for the generation layer to construct one.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from tafahhum.core.enums import EvidenceType, VerificationStatus


@dataclass(frozen=True)
class Citation:
    """Where a passage came from. Every field is read from the corpus."""

    passage_id: str
    work_slug: str
    work_title_ar: str
    work_title_en: str | None
    author_name_ar: str
    author_name_en: str | None
    author_death_year_hijri: int | None
    edition_slug: str
    edition_publisher: str | None
    edition_year: int | None
    volume: int | None
    page_start: int | None
    page_end: int | None
    scan_page_uri: str | None
    citation_precision: VerificationStatus

    @property
    def resolves_to_page(self) -> bool:
        """True only when the citation reaches an actual printed page."""
        return self.volume is not None and self.page_start is not None

    def reference_string(self, language: str = "en") -> str:
        """Human-readable citation, honest about how far it resolves."""
        if language == "ar":
            title = self.work_title_ar
            author = self.author_name_ar
        else:
            title = self.work_title_en or self.work_title_ar
            author = self.author_name_en or self.author_name_ar

        parts = [f"{author}, {title}"]
        if self.volume is not None:
            parts.append(f"vol. {self.volume}")
        if self.page_start is not None:
            page = str(self.page_start)
            if self.page_end and self.page_end != self.page_start:
                page = f"{self.page_start}-{self.page_end}"
            parts.append(f"p. {page}")
        if not self.resolves_to_page:
            parts.append("[no page-level citation available for this edition]")
        return ", ".join(parts)


@dataclass
class RetrievedPassage:
    """A passage plus how and why it was retrieved."""

    citation: Citation
    display_text: str
    normalized_text: str
    evidence_kind: EvidenceType
    verification_status: VerificationStatus
    surah_number: int | None
    ayah_start: int | None
    ayah_end: int | None
    ayah_alignment_confidence: float | None

    #: Per-strategy ranks, kept separately so fusion is explainable.
    ranks: dict[str, int] = field(default_factory=dict)
    scores: dict[str, float] = field(default_factory=dict)
    fused_score: float = 0.0
    #: Which retrieval strategies surfaced this passage.
    strategies: list[str] = field(default_factory=list)

    @property
    def passage_id(self) -> str:
        return self.citation.passage_id

    @property
    def ayah_label(self) -> str | None:
        if self.surah_number is None or self.ayah_start is None:
            return None
        if self.ayah_end and self.ayah_end != self.ayah_start:
            return f"{self.surah_number}:{self.ayah_start}-{self.ayah_end}"
        return f"{self.surah_number}:{self.ayah_start}"


@dataclass
class RetrievalTrace:
    """Why the result set looks the way it does.

    Surfaced through the "how this answer was built" panel. It records system
    decisions and evidence, not model reasoning.
    """

    strategies_run: list[str] = field(default_factory=list)
    candidates_per_strategy: dict[str, int] = field(default_factory=dict)
    filters_applied: dict[str, object] = field(default_factory=dict)
    rules_applied: list[str] = field(default_factory=list)
    fused_candidates: int = 0
    returned: int = 0
    works_represented: int = 0
