"""Producing, verifying, storing, and serving an ayah summary.

Generation runs for minutes on a local model, far longer than a proxy, a
browser, or a load balancer will hold a request open. So no request ever waits
for it. The first caller starts a background job and is told the work is
pending; callers poll until the finished summary appears in the cache.

The summary is a function of three things: the ayah, the reader's language, and
which sources were selected. Change any of them and it is a different summary
rather than a stale one, which is why the cache key covers all three.
"""

from __future__ import annotations

import threading

import psycopg

from tafahhum.core.config import get_settings
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

_in_flight: set[tuple] = set()
#: Why a job produced nothing. Failures are not written to `ayah_summary`, whose
#: constraints require a summary to name the evidence behind it, and a failure
#: has none. They are held here so a poll gets an explanation, not silence.
_failures: dict[tuple, dict] = {}
_lock = threading.Lock()

PENDING_REASON = (
    "Reading the commentaries and checking each sentence against them. "
    "This takes a few minutes on the local model."
)

NOTICE = (
    "Written by Tafahhum from the passages shown below, not by a commentator. "
    "Each sentence was matched against the passage it draws on, and any that "
    "could not be traced was removed. It summarises these sources only, and it "
    "is not a ruling."
)


def selection_key(work_slugs: list[str] | None) -> str:
    """Stable key for a source selection, order-independent."""
    return ",".join(sorted(work_slugs)) if work_slugs else "*"


def _job_key(surah: int, ayah: int, language: Language, work_slugs) -> tuple:
    return (surah, ayah, language.value, selection_key(work_slugs))


# ---------------------------------------------------------------------------
# Reading
# ---------------------------------------------------------------------------

def _passages_for(
    conn: psycopg.Connection,
    surah: int,
    ayah: int,
    work_slugs: list[str] | None,
) -> list[dict]:
    """The passages a summary may draw on.

    Passages that open a commentator's treatment of a clause are preferred, and
    at most one is taken per work: a summary should hear from many commentators
    rather than quote one at length.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT DISTINCT ON (w.slug)
                   p.id, COALESCE(p.verified_text, p.raw_text) AS text,
                   w.slug AS work_slug
            FROM published_passage p
            JOIN passage_ayah pa ON pa.passage_id = p.id
            JOIN tafsir_work w ON w.id = p.tafsir_work_id
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
                   mean_support, verification_status::text AS verification_status
            FROM ayah_summary
            WHERE surah_number = %s AND ayah_number = %s
              AND language = %s AND selection_key = %s
            """,
            (surah, ayah, language.value, selection_key(work_slugs)),
        )
        row = cur.fetchone()

    if row is None:
        return None
    return {
        "status": "ready",
        "summary": row["summary_text"],
        "model": row["model_name"],
        "generator": row["generator_version"],
        "cited_passage_ids": [str(i) for i in row["cited_passage_ids"]],
        "sentences_generated": row["sentences_generated"],
        "sentences_kept": row["sentences_kept"],
        "sentences_removed": row["sentences_removed"],
        "mean_support": row["mean_support"],
        "verification_status": row["verification_status"],
        "evidence_type": "TAFAHHUM_SYNTHESIS",
        "notice": NOTICE,
    }


# ---------------------------------------------------------------------------
# Writing
# ---------------------------------------------------------------------------

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


def _generate_and_store(
    conn: psycopg.Connection,
    surah: int,
    ayah: int,
    language: Language,
    work_slugs: list[str] | None,
) -> None:
    """The slow half, run off the request path."""
    key = _job_key(surah, ayah, language, work_slugs)
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
        _failures[key] = {
            "status": "unavailable",
            "reason": (
                "No generation backend is configured. The commentaries below "
                "are unaffected."
            ),
        }
        return

    if not result.is_usable:
        _failures[key] = {
            "status": "insufficient",
            "reason": result.note
            or (
                f"Fewer than {MIN_PASSAGES} passages are available for this "
                f"verse in the selected sources."
            ),
            "sentences_generated": result.generated,
            "sentences_removed": result.removed,
            "removed_detail": [
                {"text": s.text[:160], "reason": s.reason}
                for s in result.sentences
                if not s.kept
            ][:6],
        }
        return

    # Verified in Arabic, then rendered. Never the other way round.
    text = result.summary_ar
    if language is not Language.AR:
        translated = translate_summary(result.summary_ar, language)
        if translated:
            text = translated

    _store(conn, surah, ayah, language, work_slugs, text, result)
    _failures.pop(key, None)


# ---------------------------------------------------------------------------
# Request path
# ---------------------------------------------------------------------------

def get_or_create_summary(
    conn: psycopg.Connection,
    *,
    surah: int,
    ayah: int,
    language: Language,
    work_slugs: list[str] | None = None,
    force: bool = False,
) -> dict:
    """Return the summary if it exists, otherwise start building one.

    Returns immediately in every case, and says which of those happened, so a
    client can render a result, show progress, or explain why nothing could be
    produced.
    """
    key = _job_key(surah, ayah, language, work_slugs)

    if not force:
        cached = fetch_cached(conn, surah, ayah, language, work_slugs)
        if cached:
            return cached

    with _lock:
        running = key in _in_flight
        if not running:
            _in_flight.add(key)

    if running:
        return {
            "status": "pending",
            "summary": None,
            "reason": PENDING_REASON,
            "evidence_type": "TAFAHHUM_SYNTHESIS",
        }

    # An earlier attempt that produced nothing is reported once and then
    # cleared, so asking again retries rather than repeating the same refusal.
    previous = _failures.pop(key, None)

    def worker() -> None:
        try:
            # Its own connection: the pooled one belongs to a request that has
            # already returned by the time this runs.
            with psycopg.connect(
                get_settings().dsn, row_factory=psycopg.rows.dict_row
            ) as job_conn:
                _generate_and_store(job_conn, surah, ayah, language, work_slugs)
        except Exception as exc:
            _failures[key] = {
                "status": "unavailable",
                "reason": f"Generation failed: {exc}",
            }
        finally:
            # Always clear the key. A wedged job would otherwise leave every
            # later request polling for something that never arrives.
            with _lock:
                _in_flight.discard(key)

    threading.Thread(target=worker, daemon=True).start()

    if previous:
        return {**previous, "summary": None, "evidence_type": "TAFAHHUM_SYNTHESIS"}

    return {
        "status": "pending",
        "summary": None,
        "reason": PENDING_REASON,
        "evidence_type": "TAFAHHUM_SYNTHESIS",
    }
