"""Ingesting a Tafsir source into the corpus.

Ingestion is where provenance is either established or lost, so this module is
deliberate about what it does and does not claim.

What a digital text source can support:
  - the text itself, attributed to a named work and author
  - ayah alignment, because the source is organised by ayah

What it cannot support, and therefore must not assert:
  - volume and page numbers, because no print edition is identified
  - biographical data for the author (dates, places, teachers)
  - the identity of the edition the digital text was keyed from

Those fields are left NULL and the relevant confidence dimensions are recorded as
UNVERIFIED. A user reading such a passage is shown that its citation resolves to a
work but not to a page. Filling that gap requires ingesting an identified print
edition with scans — the pipeline in CORPUS_PIPELINE.md — not a better guess here.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path

import psycopg

from tafahhum.arabic.normalize import normalize_key
from tafahhum.core.enums import (
    AlignmentKind,
    CopyrightStatus,
    CorpusStatus,
    EvidenceType,
    HistoricalPeriod,
    Language,
    VerificationStatus,
)
from tafahhum.corpus.chunking import chunk_commentary


def _returned_id(row) -> str:
    """Read a RETURNING id from a row, whatever row factory the caller used.

    These helpers are called from several scripts, and psycopg hands back tuples
    or dicts depending on how the connection was opened. Assuming one shape made
    the ingestion crash the first time it was called from a dict_row connection.
    """
    if row is None:
        raise RuntimeError("expected a RETURNING id but got no row")
    return row["id"] if isinstance(row, dict) else row[0]


@dataclass(frozen=True)
class SourceWork:
    """Metadata for a work being ingested, as supplied by the source."""

    slug: str
    title_ar: str
    title_en: str
    author_name_ar: str
    author_name_en: str
    source_url: str
    source_name: str
    license_note: str
    # Classification, attributed to whoever made it. UNCLASSIFIED with a NULL
    # source is the honest default; the schema rejects a claim without a source.
    tradition: str = "UNCLASSIFIED"
    method: str = "UNCLASSIFIED"
    classification_source: str | None = None
    classification_source_url: str | None = None
    classification_note: str | None = None
    catalogue_rank: int = 500
    is_default_source: bool = False
    death_year_hijri: int | None = None


@dataclass(frozen=True)
class SourceCommentary:
    """One ayah's commentary from a source."""

    surah: int
    ayah: int
    text: str


@dataclass
class IngestReport:
    work_slug: str
    passages_written: int = 0
    ayahs_covered: int = 0
    skipped_empty: int = 0

    def __str__(self) -> str:
        return (
            f"{self.work_slug}: {self.passages_written} passages "
            f"across {self.ayahs_covered} ayahs "
            f"({self.skipped_empty} empty entries skipped)"
        )


# ---------------------------------------------------------------------------
# Upserts
# ---------------------------------------------------------------------------

def upsert_mufassir(cur: psycopg.Cursor, work: SourceWork) -> str:
    """Create or fetch the author record.

    Biographical fields stay NULL. A digital text index supplies a name and
    nothing else, and a death year invented here would be indistinguishable from
    one that had been verified against a biographical source.
    """
    slug = f"mufassir-{normalize_key(work.author_name_en).replace(' ', '-')}"
    # A death year is written only where the catalogue reference states one, and
    # it stays UNVERIFIED until a bibliographical source attests it to a page.
    cur.execute(
        """
        INSERT INTO mufassir
            (slug, name_ar, name_en, death_year_hijri, period,
             verification_status, biography_note)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (slug) DO UPDATE SET
            name_en = EXCLUDED.name_en,
            death_year_hijri = COALESCE(mufassir.death_year_hijri, EXCLUDED.death_year_hijri),
            period = EXCLUDED.period
        RETURNING id
        """,
        (
            slug,
            work.author_name_ar,
            work.author_name_en,
            work.death_year_hijri,
            HistoricalPeriod.from_death_year_hijri(work.death_year_hijri).value,
            VerificationStatus.UNVERIFIED.value,
            "Dates where present come from a tertiary catalogue reference and are "
            "unverified. Places and teacher/student relations require a "
            "bibliographical source.",
        ),
    )
    return _returned_id(cur.fetchone())


def upsert_work(cur: psycopg.Cursor, work: SourceWork, author_id: str) -> str:
    cur.execute(
        """
        INSERT INTO tafsir_work
            (slug, author_id, title_ar, title_en, language, corpus_state,
             verification_status, attribution_confidence, notes,
             tradition, method, classification_source, classification_source_url,
             classification_status, classification_note, catalogue_rank,
             is_default_source)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (slug) DO UPDATE SET
            corpus_state = EXCLUDED.corpus_state,
            tradition = EXCLUDED.tradition,
            method = EXCLUDED.method,
            classification_source = EXCLUDED.classification_source,
            classification_source_url = EXCLUDED.classification_source_url,
            classification_note = EXCLUDED.classification_note,
            catalogue_rank = EXCLUDED.catalogue_rank,
            is_default_source = EXCLUDED.is_default_source
        RETURNING id
        """,
        (
            work.slug,
            author_id,
            work.title_ar,
            work.title_en,
            Language.AR.value,
            CorpusStatus.PUBLISHED.value,
            VerificationStatus.UNVERIFIED.value,
            VerificationStatus.UNVERIFIED.value,
            f"Ingested from {work.source_name}. Attribution follows the source and "
            f"has not been checked against a bibliographical work.",
            work.tradition,
            work.method,
            work.classification_source,
            work.classification_source_url,
            VerificationStatus.UNVERIFIED.value,
            work.classification_note,
            work.catalogue_rank,
            work.is_default_source,
        ),
    )
    return _returned_id(cur.fetchone())


def upsert_edition(cur: psycopg.Cursor, work: SourceWork, work_id: str) -> str:
    """Register the digital text as an edition with no print provenance.

    Modelling it as an edition rather than attaching passages to the work keeps
    the invariant that every citation resolves to a specific text, and makes the
    absence of page numbers an explicit property of *this* edition rather than a
    silent gap.
    """
    cur.execute(
        """
        INSERT INTO edition
            (slug, tafsir_work_id, publisher, digital_source_url, scan_source,
             copyright_status, license_note, corpus_state, verification_status,
             edition_quality_note, is_critical_edition)
        VALUES (%s, %s, %s, %s, NULL, %s, %s, %s, %s, %s, false)
        ON CONFLICT (slug) DO UPDATE SET corpus_state = EXCLUDED.corpus_state
        RETURNING id
        """,
        (
            f"{work.slug}-digital",
            work_id,
            None,
            work.source_url,
            CopyrightStatus.UNKNOWN.value,
            work.license_note,
            CorpusStatus.PUBLISHED.value,
            VerificationStatus.UNVERIFIED.value,
            "Digital text with no identified print edition. Volume and page are "
            "unavailable, so citations resolve to the work but not to a page.",
        ),
    )
    return _returned_id(cur.fetchone())


# ---------------------------------------------------------------------------
# Passage ingestion
# ---------------------------------------------------------------------------

def ingest_commentaries(
    conn: psycopg.Connection,
    work: SourceWork,
    commentaries: Iterable[SourceCommentary],
    *,
    replace: bool = True,
) -> IngestReport:
    """Ingest a work's commentaries, chunked into passages."""
    report = IngestReport(work_slug=work.slug)

    with conn.cursor() as cur:
        author_id = upsert_mufassir(cur, work)
        work_id = upsert_work(cur, work, author_id)
        edition_id = upsert_edition(cur, work, work_id)

        if replace:
            cur.execute("DELETE FROM passage WHERE edition_id = %s", (edition_id,))

        sequence = 0
        for entry in commentaries:
            if not entry.text or not entry.text.strip():
                report.skipped_empty += 1
                continue

            chunks = chunk_commentary(entry.text)
            if not chunks:
                report.skipped_empty += 1
                continue

            for chunk in chunks:
                cur.execute(
                    """
                    INSERT INTO passage
                        (edition_id, tafsir_work_id, author_id, sequence_index,
                         raw_text, normalized_text, evidence_kind, language,
                         citation_precision, verification_status,
                         volume, page_start, page_end)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NULL, NULL, NULL)
                    RETURNING id
                    """,
                    (
                        edition_id,
                        work_id,
                        author_id,
                        sequence,
                        chunk.raw_text,
                        chunk.normalized_text,
                        EvidenceType.MUFASSIR_INTERPRETATION.value,
                        Language.AR.value,
                        # No print edition means no page-level citation. This is
                        # the honest value, and the UI surfaces it to the reader.
                        VerificationStatus.UNVERIFIED.value,
                        VerificationStatus.UNVERIFIED.value,
                    ),
                )
                passage_id = cur.fetchone()[0]
                sequence += 1
                report.passages_written += 1

                cur.execute(
                    """
                    INSERT INTO passage_ayah
                        (passage_id, surah_number, ayah_start, ayah_end,
                         alignment, confidence, verification_status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        passage_id,
                        entry.surah,
                        entry.ayah,
                        entry.ayah,
                        AlignmentKind.PRIMARY.value,
                        # The source is organised by ayah, so alignment is
                        # structural rather than inferred — high confidence.
                        0.99,
                        VerificationStatus.MACHINE_PROPOSED.value,
                    ),
                )
            report.ayahs_covered += 1

        conn.commit()
    return report


# ---------------------------------------------------------------------------
# File-based source adapter
# ---------------------------------------------------------------------------

def read_commentary_dir(path: Path) -> Iterator[SourceCommentary]:
    """Read commentaries from a directory of ``{surah}/{ayah}.json`` files."""
    for surah_dir in sorted(path.iterdir(), key=lambda p: int(p.name) if p.name.isdigit() else 0):
        if not surah_dir.is_dir() or not surah_dir.name.isdigit():
            continue
        files = sorted(
            (f for f in surah_dir.glob("*.json")),
            key=lambda f: int(f.stem) if f.stem.isdigit() else 0,
        )
        for f in files:
            data = json.loads(f.read_text(encoding="utf-8"))
            text = data.get("text") or ""
            yield SourceCommentary(
                surah=int(data.get("surah", surah_dir.name)),
                ayah=int(data.get("ayah", f.stem)),
                text=text,
            )
