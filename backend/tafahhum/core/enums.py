"""Enumerations shared across the system.

These mirror the PostgreSQL enum types defined in `migrations/`. The pairing is
checked by `tests/test_enum_parity.py`, which reads the migration files and fails
if the two drift apart — a silent mismatch would surface as a runtime cast error
deep inside a query rather than at import time.
"""

from __future__ import annotations

from enum import StrEnum


class Language(StrEnum):
    """Languages the user interface supports, plus corpus languages."""

    AR = "ar"
    EN = "en"
    UR = "ur"
    FA = "fa"
    TR = "tr"
    MS = "ms"
    OTHER = "other"

    @property
    def is_rtl(self) -> bool:
        return self in (Language.AR, Language.UR, Language.FA)

    @property
    def endonym(self) -> str:
        return {
            Language.AR: "العربية",
            Language.EN: "English",
            Language.UR: "اردو",
            Language.FA: "فارسی",
            Language.TR: "Türkçe",
            Language.MS: "Bahasa Melayu",
            Language.OTHER: "—",
        }[self]


#: The pivot language of the system. All retrieval happens here.
PIVOT_LANGUAGE = Language.AR

#: Languages a user may choose for querying and presentation.
USER_LANGUAGES = (Language.AR, Language.EN, Language.UR)


class CorpusStatus(StrEnum):
    DISCOVERED = "DISCOVERED"
    ACQUIRED = "ACQUIRED"
    SCANNED = "SCANNED"
    OCR_COMPLETE = "OCR_COMPLETE"
    NORMALIZED = "NORMALIZED"
    AYAH_ALIGNED = "AYAH_ALIGNED"
    METADATA_COMPLETE = "METADATA_COMPLETE"
    HUMAN_REVIEW = "HUMAN_REVIEW"
    VERIFIED = "VERIFIED"
    INDEXED = "INDEXED"
    PUBLISHED = "PUBLISHED"


class VerificationStatus(StrEnum):
    FIXTURE = "FIXTURE"
    UNVERIFIED = "UNVERIFIED"
    MACHINE_PROPOSED = "MACHINE_PROPOSED"
    IN_REVIEW = "IN_REVIEW"
    DISPUTED = "DISPUTED"
    VERIFIED = "VERIFIED"


class EvidenceType(StrEnum):
    """The eight kinds of evidence that must never be silently merged."""

    QURANIC_TEXT = "QURANIC_TEXT"
    HADITH = "HADITH"
    COMPANION_REPORT = "COMPANION_REPORT"
    TABII_REPORT = "TABII_REPORT"
    MUFASSIR_INTERPRETATION = "MUFASSIR_INTERPRETATION"
    LATER_SCHOLARLY_INTERPRETATION = "LATER_SCHOLARLY_INTERPRETATION"
    MODERN_ACADEMIC_ANALYSIS = "MODERN_ACADEMIC_ANALYSIS"
    TAFAHHUM_SYNTHESIS = "TAFAHHUM_SYNTHESIS"

    @property
    def is_source_material(self) -> bool:
        """False only for Tafahhum's own synthesis, which is never a citation."""
        return self is not EvidenceType.TAFAHHUM_SYNTHESIS


class HistoricalPeriod(StrEnum):
    FORMATIVE = "FORMATIVE"
    EARLY = "EARLY"
    CLASSICAL = "CLASSICAL"
    MEDIEVAL = "MEDIEVAL"
    LATER = "LATER"
    MODERN = "MODERN"
    UNKNOWN = "UNKNOWN"

    @classmethod
    def from_death_year_hijri(cls, year: int | None) -> HistoricalPeriod:
        """Assign a period from a Hijri death year.

        The boundaries are conventional and contested; this is a retrieval
        convenience for chronological ordering, not a scholarly claim. The
        authoritative field remains the death year itself, which is what
        historical-mode queries actually sort on.
        """
        if year is None:
            return cls.UNKNOWN
        if year <= 150:
            return cls.FORMATIVE
        if year <= 400:
            return cls.EARLY
        if year <= 700:
            return cls.CLASSICAL
        if year <= 1000:
            return cls.MEDIEVAL
        if year <= 1300:
            return cls.LATER
        return cls.MODERN


class CoverageKind(StrEnum):
    COMPLETE = "COMPLETE"
    PARTIAL = "PARTIAL"
    FRAGMENTARY = "FRAGMENTARY"
    LOST = "LOST"
    UNKNOWN = "UNKNOWN"


class CopyrightStatus(StrEnum):
    PUBLIC_DOMAIN = "PUBLIC_DOMAIN"
    PUBLIC_DOMAIN_TEXT_EDITION_RESTRICTED = "PUBLIC_DOMAIN_TEXT_EDITION_RESTRICTED"
    LICENSED = "LICENSED"
    RESTRICTED = "RESTRICTED"
    UNKNOWN = "UNKNOWN"


class AlignmentKind(StrEnum):
    PRIMARY = "PRIMARY"
    DISCUSSED = "DISCUSSED"
    CITED = "CITED"
    CROSS_REFERENCE = "CROSS_REFERENCE"


class QueryType(StrEnum):
    AYAH_TAFSIR = "AYAH_TAFSIR"
    WORD_MEANING = "WORD_MEANING"
    LINGUISTIC = "LINGUISTIC"
    ASBAB_AL_NUZUL = "ASBAB_AL_NUZUL"
    FIQH = "FIQH"
    AQEEDAH = "AQEEDAH"
    HADITH = "HADITH"
    QIRAAT = "QIRAAT"
    HISTORICAL = "HISTORICAL"
    COMPARATIVE = "COMPARATIVE"
    MUFASSIR_SPECIFIC = "MUFASSIR_SPECIFIC"
    TAFSIR_SPECIFIC = "TAFSIR_SPECIFIC"
    THEMATIC = "THEMATIC"
    SCHOLARLY_DISAGREEMENT = "SCHOLARLY_DISAGREEMENT"
    MUFASSIR_BIOGRAPHY = "MUFASSIR_BIOGRAPHY"
    SOURCE_SEARCH = "SOURCE_SEARCH"
    UNKNOWN = "UNKNOWN"


class RuleTier(StrEnum):
    """Evaluation tiers. A lower tier never overrides a higher one."""

    SYSTEM_INTEGRITY = "SYSTEM_INTEGRITY"
    SOURCE_PROVENANCE = "SOURCE_PROVENANCE"
    SCHOLARLY_METHOD = "SCHOLARLY_METHOD"
    QUERY_STRATEGY = "QUERY_STRATEGY"
    EVIDENCE_QUALITY = "EVIDENCE_QUALITY"
    RESPONSE_STRUCTURE = "RESPONSE_STRUCTURE"
    LANGUAGE_GENERATION = "LANGUAGE_GENERATION"

    @property
    def rank(self) -> int:
        return list(RuleTier).index(self)


class AnswerMode(StrEnum):
    SIMPLE = "SIMPLE"
    DETAILED = "DETAILED"
    COMPARATIVE = "COMPARATIVE"
    RESEARCH = "RESEARCH"
    SOURCE = "SOURCE"
    HISTORICAL = "HISTORICAL"


#: Sentinel for rules that make no scholarly claim and are attributed to no book.
BASELINE_SOURCE_BOOK = "TAFAHHUM_BASELINE"
