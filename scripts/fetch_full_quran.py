"""Ingest commentary for the whole Quran.

    python scripts/fetch_full_quran.py --works default     # the 12 default works
    python scripts/fetch_full_quran.py --works all         # every catalogued work
    python scripts/fetch_full_quran.py --fetch-only        # download, do not ingest
    python scripts/fetch_full_quran.py --ingest-only       # ingest what is cached

Fetches a whole surah per request rather than a whole ayah per request: 114 calls
per work instead of 6,236, which is the difference between minutes and a day.

Both phases are resumable. Downloads skip files already on disk, and ingestion
replaces a work's passages transactionally per surah, so an interrupted run can
be restarted without producing duplicates or half-written surahs.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import httpx
import psycopg

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from tafahhum.arabic.normalize import normalize_for_matching  # noqa: E402
from tafahhum.core.config import get_settings  # noqa: E402
from tafahhum.core.enums import (  # noqa: E402
    AlignmentKind,
    EvidenceType,
    Language,
    VerificationStatus,
)
from tafahhum.corpus.catalogue import (  # noqa: E402
    CATALOGUE,
    CLASSIFICATION_SOURCE,
    CLASSIFICATION_SOURCE_URL,
)
from tafahhum.corpus.chunking import chunk_commentary  # noqa: E402
from tafahhum.corpus.ingest import SourceWork, upsert_edition, upsert_mufassir, upsert_work  # noqa: E402
from tafahhum.quran.surah_data import SURAHS  # noqa: E402

CACHE = ROOT / "data" / "seed" / "surah"
BASE = "https://raw.githubusercontent.com/spa5k/tafsir_api/main/tafsir"
SOURCE_NAME = "spa5k/tafsir_api (aggregating quran.com)"
LICENSE_NOTE = (
    "Text obtained from an open aggregation of digital Tafsir editions. The "
    "underlying print edition is not identified by the source, so edition-level "
    "licence status is UNKNOWN and must be established before redistribution."
)


def cache_path(source_slug: str, surah: int) -> Path:
    return CACHE / source_slug / f"{surah}.json"


def read_records(path: Path) -> list[dict]:
    """The cached records for one surah, whichever shape the source used.

    Most works come back as a bare list of ayah records. One,
    ar-tafseer-tanwir-al-miqbas, wraps them as {"ayahs": [...]}, and iterating
    that dict yields the string key rather than a record, which took the whole
    ingest down with an AttributeError partway through. Both shapes are
    accepted here, and anything else yields nothing rather than a crash: one
    malformed work must not cost the other forty-nine.
    """
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        data = data.get("ayahs") or data.get("data") or []
    if not isinstance(data, list):
        return []
    return [r for r in data if isinstance(r, dict)]


# ---------------------------------------------------------------------------
# Phase 1 — download
# ---------------------------------------------------------------------------

def fetch_surah(client: httpx.Client, source_slug: str, surah: int) -> tuple[str, int, bool]:
    dest = cache_path(source_slug, surah)
    if dest.exists() and dest.stat().st_size > 2:
        return source_slug, surah, True

    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        r = client.get(f"{BASE}/{source_slug}/{surah}.json", timeout=90)
        if r.status_code == 200:
            dest.write_text(r.text, encoding="utf-8")
            return source_slug, surah, True
        if r.status_code == 404:
            # Not every work covers every surah. Record the gap so the next run
            # does not retry it forever.
            dest.write_text("[]", encoding="utf-8")
            return source_slug, surah, True
    except httpx.HTTPError:
        return source_slug, surah, False
    return source_slug, surah, False


def download(works: list, workers: int = 10) -> None:
    jobs = [(w.source_slug, s.number) for w in works for s in SURAHS]
    pending = [j for j in jobs if not cache_path(*j).exists()]
    print(f"download: {len(jobs)} surah files, {len(pending)} missing")
    if not pending:
        return

    done = failed = 0
    started = time.time()
    with httpx.Client(follow_redirects=True) as client:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = [pool.submit(fetch_surah, client, s, n) for s, n in pending]
            for f in as_completed(futures):
                _, _, ok = f.result()
                done += 1
                failed += 0 if ok else 1
                if done % 200 == 0 or done == len(pending):
                    rate = done / max(1e-6, time.time() - started)
                    print(
                        f"  {done}/{len(pending)}  {rate:.0f}/s  {failed} failed",
                        flush=True,
                    )
    print(f"download complete: {failed} failed")


# ---------------------------------------------------------------------------
# Phase 2 — ingest
# ---------------------------------------------------------------------------

def ingest_work(conn: psycopg.Connection, entry) -> tuple[int, int]:
    """Ingest every cached surah for one work. Returns (passages, surahs)."""
    work = SourceWork(
        slug=entry.slug,
        title_ar=entry.title_ar,
        title_en=entry.title_en,
        author_name_ar=entry.author_ar,
        author_name_en=entry.author_en,
        source_url=f"{BASE}/{entry.source_slug}",
        source_name=SOURCE_NAME,
        license_note=LICENSE_NOTE,
        tradition=entry.tradition,
        method=entry.method,
        classification_source=(
            None if entry.tradition == "UNCLASSIFIED" else CLASSIFICATION_SOURCE
        ),
        classification_source_url=(
            None if entry.tradition == "UNCLASSIFIED" else CLASSIFICATION_SOURCE_URL
        ),
        classification_note=entry.note,
        catalogue_rank=entry.rank,
        is_default_source=entry.default,
        death_year_hijri=entry.death_hijri,
    )

    with conn.cursor() as cur:
        author_id = upsert_mufassir(cur, work)
        work_id = upsert_work(cur, work, author_id)
        edition_id = upsert_edition(cur, work, work_id)
        # A full re-ingest of this work: drop what is there so a rerun cannot
        # double-insert. Scoped to one work so other works stay untouched.
        cur.execute("DELETE FROM passage WHERE edition_id = %s", (edition_id,))
    conn.commit()

    sequence = 0
    total = 0
    surahs_done = 0

    for surah in SURAHS:
        path = cache_path(entry.source_slug, surah.number)
        if not path.exists():
            continue
        try:
            records = read_records(path)
        except json.JSONDecodeError:
            continue
        if not records:
            continue

        rows: list[tuple] = []
        for rec in records:
            text = (rec.get("text") or "").strip()
            if not text:
                continue
            ayah_no = int(rec.get("ayah") or 0)
            if ayah_no < 1 or ayah_no > surah.ayah_count:
                continue
            for chunk in chunk_commentary(text):
                rows.append(
                    (
                        edition_id, work_id, author_id, sequence,
                        chunk.raw_text, chunk.normalized_text,
                        EvidenceType.MUFASSIR_INTERPRETATION.value,
                        Language.AR.value,
                        VerificationStatus.UNVERIFIED.value,
                        VerificationStatus.UNVERIFIED.value,
                        surah.number, ayah_no,
                    )
                )
                sequence += 1

        if not rows:
            continue

        # One statement per surah rather than per chunk: at this volume the
        # round-trip cost dominates everything else.
        with conn.cursor() as cur:
            cur.executemany(
                """
                WITH inserted AS (
                    INSERT INTO passage
                        (edition_id, tafsir_work_id, author_id, sequence_index,
                         raw_text, normalized_text, evidence_kind, language,
                         citation_precision, verification_status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                )
                INSERT INTO passage_ayah
                    (passage_id, surah_number, ayah_start, ayah_end,
                     alignment, confidence, verification_status)
                SELECT id, %s, %s, %s, 'PRIMARY', 0.99, 'MACHINE_PROPOSED'
                FROM inserted
                """,
                [(*r[:10], r[10], r[11], r[11]) for r in rows],
            )
        conn.commit()
        total += len(rows)
        surahs_done += 1

    return total, surahs_done


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--works", choices=["default", "all"], default="default")
    ap.add_argument("--fetch-only", action="store_true")
    ap.add_argument("--ingest-only", action="store_true")
    ap.add_argument("--workers", type=int, default=10)
    args = ap.parse_args()

    works = [e for e in CATALOGUE if e.default] if args.works == "default" else list(CATALOGUE)
    works.sort(key=lambda e: e.rank)
    print(f"{len(works)} work(s) x {len(SURAHS)} surahs = {len(works) * len(SURAHS)} files")

    if not args.ingest_only:
        download(works, workers=args.workers)
    if args.fetch_only:
        return 0

    settings = get_settings()
    grand = 0
    with psycopg.connect(settings.dsn, row_factory=psycopg.rows.dict_row) as conn:
        for i, entry in enumerate(works, start=1):
            started = time.time()
            passages, surahs = ingest_work(conn, entry)
            grand += passages
            print(
                f"  [{i}/{len(works)}] {entry.slug:42} "
                f"{passages:>7} passages, {surahs:>3} surahs, {time.time() - started:.0f}s",
                flush=True,
            )
    print(f"\ntotal passages ingested: {grand}")
    print("next: python scripts/build_phrases.py   # derive clause structure")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
