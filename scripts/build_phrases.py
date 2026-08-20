"""Derive the clause structure of every indexed ayah and align passages to it.

    python scripts/build_phrases.py            # all ayahs with commentary
    python scripts/build_phrases.py --ayah 2:255

Derived data. Safe to re-run after ingesting more commentaries — a wider corpus
gives better-attested clause boundaries, and rebuilding simply replaces the
previous derivation.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import psycopg

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from tafahhum.core.config import get_settings  # noqa: E402
from tafahhum.quran.phrases import (  # noqa: E402
    align_passage,
    passage_gist,
    segment_ayah,
)


def ayahs_with_commentary(conn: psycopg.Connection) -> list[tuple[int, int]]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT DISTINCT pa.surah_number, pa.ayah_start
            FROM passage_ayah pa
            JOIN passage p ON p.id = pa.passage_id
            ORDER BY 1, 2
            """
        )
        return [(r["surah_number"], r["ayah_start"]) for r in cur.fetchall()]


def build_for_ayah(conn: psycopg.Connection, surah: int, ayah: int) -> tuple[int, int, int]:
    """Returns (phrases, passages, aligned)."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT a.text_uthmani FROM ayah a
            JOIN quran_text_source q ON q.id = a.text_source_id
            WHERE q.is_default AND a.surah_number = %s AND a.ayah_number = %s
            """,
            (surah, ayah),
        )
        row = cur.fetchone()
        if row is None:
            return 0, 0, 0
        ayah_text = row["text_uthmani"]

        cur.execute(
            """
            SELECT p.id, COALESCE(p.verified_text, p.raw_text) AS text
            FROM passage p
            JOIN passage_ayah pa ON pa.passage_id = p.id
            WHERE pa.surah_number = %s AND pa.ayah_start = %s
            """,
            (surah, ayah),
        )
        passages = cur.fetchall()

    if not passages:
        return 0, 0, 0

    phrases = segment_ayah(ayah_text, [p["text"] for p in passages])

    with conn.cursor() as cur:
        # Replace rather than merge: the derivation is a whole-ayah result, and
        # a partial update would leave stale boundaries beside fresh ones.
        cur.execute(
            "DELETE FROM ayah_phrase WHERE surah_number = %s AND ayah_number = %s",
            (surah, ayah),
        )

        phrase_ids: dict[int, str] = {}
        for phrase in phrases:
            cur.execute(
                """
                INSERT INTO ayah_phrase
                    (surah_number, ayah_number, phrase_index, start_word, end_word,
                     text_ar, normalized, support)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    surah, ayah, phrase.index, phrase.start_word, phrase.end_word,
                    phrase.text, phrase.normalized, phrase.support,
                ),
            )
            phrase_ids[phrase.index] = cur.fetchone()["id"]

        aligned = 0
        for p in passages:
            alignment = align_passage(str(p["id"]), p["text"], ayah_text, phrases)
            if alignment is None:
                continue
            cur.execute(
                """
                INSERT INTO passage_phrase
                    (passage_id, phrase_id, basis, matched_words, confidence,
                     gist, opens_discussion)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (passage_id, phrase_id) DO UPDATE SET
                    basis = EXCLUDED.basis,
                    matched_words = EXCLUDED.matched_words,
                    confidence = EXCLUDED.confidence,
                    gist = EXCLUDED.gist,
                    opens_discussion = EXCLUDED.opens_discussion
                """,
                (
                    p["id"],
                    phrase_ids[alignment.phrase_index],
                    alignment.basis.upper(),
                    alignment.matched_words,
                    alignment.confidence,
                    passage_gist(p["text"]),
                    alignment.opens_discussion,
                ),
            )
            aligned += 1

    conn.commit()
    return len(phrases), len(passages), aligned


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ayah", help="single reference, e.g. 2:255")
    args = ap.parse_args()

    settings = get_settings()
    with psycopg.connect(settings.dsn, row_factory=psycopg.rows.dict_row) as conn:
        if args.ayah:
            surah, ayah = (int(x) for x in args.ayah.split(":"))
            targets = [(surah, ayah)]
        else:
            targets = ayahs_with_commentary(conn)

        print(f"deriving clause structure for {len(targets)} ayah(s)")
        total_phrases = total_aligned = total_passages = 0
        for surah, ayah in targets:
            phrases, passages, aligned = build_for_ayah(conn, surah, ayah)
            total_phrases += phrases
            total_passages += passages
            total_aligned += aligned
            pct = f"{aligned / passages:.0%}" if passages else "-"
            print(f"  {surah}:{ayah:<4} {phrases:>3} clauses  {aligned:>4}/{passages:<4} aligned {pct}")

    coverage = total_aligned / total_passages if total_passages else 0
    print(
        f"\n{total_phrases} clauses, {total_aligned}/{total_passages} passages "
        f"aligned ({coverage:.0%})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
