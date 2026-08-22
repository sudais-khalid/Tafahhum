"""Producing, verifying, storing, and serving an ayah summary.

The summary is expensive to make and cheap to reuse, and it is a function of
three things: the ayah, the reader's language, and which sources were selected.
Change any of those and it is a different summary rather than a stale one, which
is why the cache key includes all three.
"""

from __future__ import annotations

import psycopg

from tafahhum.core.enums import Language, VerificationStatus
from tafahhum.generation.summarise import (
    GENERATOR_VERSION,
    MIN_PASSAGES,
    SummaryResult,
    summarise,
    translate_summary,
)

#: How many passages are put in front of the model. Enough for breadth across
#: commentators, few enough that a small local model can hold them.
MAX_PASSAGES = 10


def selection_key(work_slugs: list[str] | None) -> str:
    """Stable key for a source selection, order-independent."""
    return ",".join(sorted(work_slugs)) if work_slugs else "*"


def _passages_for(
    conn: psycopg.Connection,
    surah: int,
    ayah: int,
    work_slugs: list[str] | None,
) -> list[dict]:
    """The passages a summary may draw on.

    Passages that open a commentator's treatment of a clause are preferred, and
    at most one is taken per work — a summary should hear from many commentators
    rather than a long extract from one.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT DISTINCT ON (w.slug)
                   p.id, COALESCE(p.verified_text, p.raw_text) AS text,
                   w.slug AS work_slug, m.name_ar AS author_ar
            FROM published_passage p
            JOIN passage_ayah pa ON pa.passage_id = p.id
            JOIN tafsir_work w ON w.id = p.tafsir_work_id
            LEFT JOIN mufassir m ON m.id = p.author_id
            LEFT JOIN passage_phrase pp ON pp.passage_id = p.id
            WHERE pa.surah_number = %s AND pa.ayah_start = %s
              AND (%s::text[] IS NULL OR w.slug = ANY(%s::text[]))
            ORDER BY w.slug,
                     (pp.opens_discussion IS TRUE) DESC NULLS LAST,
                     p.sequence_index
            """,
            (surah, ayah, work_slugs, work_slugs),
        )
        rows = cur.fetchall()

    return [
        {"id": str(r["id"]), "text": r["text"], "work_slug": r["work_slug"]}
        for r in rows[:MAX_PASSAGES]
    ]


def fetch_cached(
    conn: psycopg.Connection,
    surah: int,
    ayah: int,
    language: Language,
    work_slugs: list[str] | None,
) -> dict | None:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT summary_text, model_name, generator_version, cited_passage_ids,
                   sentences_generated, sentences_kept, sentences_removed,
                   mean_support, verification_status::text AS verification_status,
                   created_at
            FROM ayah_summary
            WHERE surah_number = %s AND ayah_number = %s
              AND language = %s AND selection_key = %s
            """,
            (surah, ayah, language.value, selection_key(work_slugs)),
        )
        return cur.fetchone()


def _store(
    conn: psycopg.Connection,
    surah: int,
    ayah: int,
    language: Language,
    work_slugs: list[str] | None,
    text: str,
    result: SummaryResult,
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO ayah_summary
                (surah_number, ayah_number, language, summary_text, raw_output,
                 model_name, generator_version, source_work_slugs, selection_key,
                 cited_passage_ids, sentences_generated, sentences_kept,
                 sentences_removed, mean_support, verification_status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s::uuid[], %s, %s, %s, %s, %s)
            ON CONFLICT (surah_number, ayah_number, language, selection_key)
            DO UPDATE SET
                summary_text = EXCLUDED.summary_text,
                raw_output = EXCLUDED.raw_output,
                model_name = EXCLUDED.model_name,
                cited_passage_ids = EXCLUDED.cited_passage_ids,
                sentences_generated = EXCLUDED.sentences_generated,
                sentences_kept = EXCLUDED.sentences_kept,
                sentences_removed = EXCLUDED.sentences_removed,
                mean_support = EXCLUDED.mean_support,
                created_at = now()
            """,
            (
                surah, ayah, language.value, text, result.raw_output,
                result.model_name, GENERATOR_VERSION,
                work_slugs or [], selection_key(work_slugs),
                result.cited_passage_ids,
                result.generated, result.kept, result.removed,
                result.mean_support,
                VerificationStatus.MACHINE_PROPOSED.value,
            ),
        )
    conn.commit()


def get_or_create_summary(
    conn: psycopg.Connection,
    *,
    surah: int,
    ayah: int,
    language: Language,
    work_slugs: list[str] | None = None,
    force: bool = False,
) -> dict:
    """Return a summary for this ayah, generating one if none is cached.

    The response always states how it was produced: how many sentences the model
    wrote, how many survived verification, and the mean overlap of those that
    did. A summary that had sentences removed is not a failure to hide — it is
    the filter working, and a reader is entitled to see that it ran.
    """
    if not force:
        cached = fetch_cached(conn, surah, ayah, language, work_slugs)
        if cached:
            return {
                "status": "cached",
                "summary": cached["summary_text"],
                "model": cached["model_name"],
                "generator": cached["generator_version"],
                "cited_passage_ids": [str(i) for i in cached["cited_passage_ids"]],
                "sentences_generated": cached["sentences_generated"],
                "sentences_kept": cached["sentences_kept"],
                "sentences_removed": cached["sentences_removed"],
                "mean_support": cached["mean_support"],
                "verification_status": cached["verification_status"],
                "evidence_type": "TAFAHHUM_SYNTHESIS",
            }

    passages = _passages_for(conn, surah, ayah, work_slugs)

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
    ayah_text = row["text_uthmani"] if row else ""

    result = summarise(ayah_text, f"{surah}:{ayah}", passages)

    if result is None:
        return {
            "status": "unavailable",
            "summary": None,
            "reason": (
                "No generation backend is configured. The commentaries "
                "themselves are unaffected and are shown above."
            ),
            "evidence_type": "TAFAHHUM_SYNTHESIS",
        }

    if not result.is_usable:
        return {
            "status": "insufficient",
            "summary": None,
            "reason": result.note
            or (
                f"Fewer than {MIN_PASSAGES} passages are available for this verse "
                f"in the selected sources."
            ),
            "sentences_generated": result.generated,
            "sentences_removed": result.removed,
            "evidence_type": "TAFAHHUM_SYNTHESIS",
        }

    # Verified in Arabic, then rendered. Never the other way round.
    text = result.summary_ar
    if language is not Language.AR:
        translated = translate_summary(result.summary_ar, language)
        if translated:
            text = translated

    _store(conn, surah, ayah, language, work_slugs, text, result)

    return {
        "status": "generated",
        "summary": text,
        "summary_ar": result.summary_ar,
        "model": result.model_name,
        "generator": GENERATOR_VERSION,
        "cited_passage_ids": result.cited_passage_ids,
        "sentences_generated": result.generated,
        "sentences_kept": result.kept,
        "sentences_removed": result.removed,
        "mean_support": result.mean_support,
        "removed_detail": [
            {"text": s.text[:160], "reason": s.reason}
            for s in result.sentences
            if not s.kept
        ],
        "verification_status": VerificationStatus.MACHINE_PROPOSED.value,
        "evidence_type": "TAFAHHUM_SYNTHESIS",
        "notice": (
            "Written by Tafahhum from the passages listed above, not by a "
            "commentator. Every sentence was checked against the passage it "
            "cites and any that could not be traced was removed. It is a "
            "summary of these sources only, not a ruling and not a settled "
            "position."
        ),
    }
