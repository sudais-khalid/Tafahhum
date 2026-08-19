"""Pre-translate the corpus into the user languages.

Translating on demand works, but makes the first reader of every passage wait
and pay. Pre-translating turns the reading path into a cache hit: the query
response already carries the translation, and the page renders in one pass.

    python scripts/translate_corpus.py --status
    python scripts/translate_corpus.py --language en --batch
    python scripts/translate_corpus.py --language ur --batch --limit 200

Uses the Batches API: half price, and 2,432 passages per language is exactly the
kind of bulk job it exists for. Nothing produced here is verified — every row is
MACHINE_PROPOSED and the interface labels it as such.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import psycopg

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from tafahhum.core.config import get_settings  # noqa: E402
from tafahhum.core.enums import Language, VerificationStatus  # noqa: E402
from tafahhum.language.translate import (  # noqa: E402
    _LANG_NAME,
    _SYSTEM,
    ClaudeTranslator,
    Translation,
    store,
)


def pending(conn: psycopg.Connection, target: Language, limit: int | None) -> list[dict]:
    """Passages with no translation in the target language yet."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT p.id, COALESCE(p.verified_text, p.raw_text) AS text,
                   p.language::text AS language
            FROM published_passage p
            WHERE p.language <> %s
              AND NOT EXISTS (
                  SELECT 1 FROM passage_translation t
                  WHERE t.passage_id = p.id AND t.language = %s
              )
            ORDER BY p.tafsir_work_id, p.sequence_index
            LIMIT %s
            """,
            (target.value, target.value, limit if limit else 100000),
        )
        return cur.fetchall()


def cmd_status() -> int:
    settings = get_settings()
    with psycopg.connect(settings.dsn, row_factory=psycopg.rows.dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT count(*) AS n FROM published_passage")
            total = cur.fetchone()["n"]
            cur.execute(
                """
                SELECT language::text AS language, count(*) AS n,
                       count(*) FILTER (WHERE verification_status = 'VERIFIED') AS verified
                FROM passage_translation GROUP BY language ORDER BY language
                """
            )
            rows = cur.fetchall()

    print(f"published passages : {total}")
    if not rows:
        print("translations       : none yet")
    for r in rows:
        pct = (r["n"] / total * 100) if total else 0
        print(
            f"  {r['language']}: {r['n']}/{total} ({pct:.0f}%), "
            f"{r['verified']} human-verified"
        )
    return 0


def cmd_translate(target: Language, limit: int | None, use_batch: bool) -> int:
    settings = get_settings()
    translator = ClaudeTranslator()

    if not translator.available():
        print(
            "No translation backend configured.\n"
            "  Run `ant auth login`, or export ANTHROPIC_API_KEY, then retry.",
            file=sys.stderr,
        )
        return 2

    with psycopg.connect(settings.dsn, row_factory=psycopg.rows.dict_row) as conn:
        rows = pending(conn, target, limit)
        if not rows:
            print(f"nothing pending for {target.value}")
            return 0

        print(f"{len(rows)} passage(s) to translate into {_LANG_NAME[target]}")

        if not use_batch:
            for i, row in enumerate(rows, start=1):
                result = translator.translate(
                    row["text"], target=target, source=Language(row["language"])
                )
                if result.text:
                    store(conn, str(row["id"]), result)
                if i % 25 == 0:
                    print(f"  {i}/{len(rows)}")
            print(f"translated {len(rows)} passage(s)")
            return 0

        return _run_batch(conn, translator, rows, target)


def _run_batch(
    conn: psycopg.Connection,
    translator: ClaudeTranslator,
    rows: list[dict],
    target: Language,
) -> int:
    from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
    from anthropic.types.messages.batch_create_params import Request

    requests = [
        Request(
            custom_id=str(r["id"]),
            params=MessageCreateParamsNonStreaming(
                model=translator.model,
                max_tokens=8000,
                # The instruction block is identical for every passage, so it is
                # marked cacheable: the batch pays for it once rather than 2,432
                # times.
                system=[
                    {
                        "type": "text",
                        "text": _SYSTEM,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                messages=[
                    {
                        "role": "user",
                        "content": (
                            f"Translate this {_LANG_NAME[Language(r['language'])]} "
                            f"passage into {_LANG_NAME[target]}.\n\n{r['text']}"
                        ),
                    }
                ],
            ),
        )
        for r in rows
    ]

    batch = translator.client.messages.batches.create(requests=requests)
    print(f"batch {batch.id} submitted with {len(requests)} passages")

    while True:
        batch = translator.client.messages.batches.retrieve(batch.id)
        if batch.processing_status == "ended":
            break
        print(f"  {batch.processing_status}: {batch.request_counts.processing} processing")
        time.sleep(30)

    stored = failed = 0
    # Results arrive in any order, so they are keyed by custom_id — which is the
    # passage id — and never by position.
    for result in translator.client.messages.batches.results(batch.id):
        if result.result.type != "succeeded":
            failed += 1
            continue
        msg = result.result.message
        text = "".join(b.text for b in msg.content if b.type == "text").strip()
        if not text:
            failed += 1
            continue
        store(
            conn,
            result.custom_id,
            Translation(
                text=text,
                language=target,
                translator_kind="MACHINE",
                translator_name=translator.name,
                model_name=translator.model,
                verification_status=VerificationStatus.MACHINE_PROPOSED,
            ),
        )
        stored += 1

    print(f"stored {stored}, failed {failed}; all MACHINE_PROPOSED pending review")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--language", choices=["en", "ur"], help="target language")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--batch", action="store_true", help="use the Batches API")
    args = ap.parse_args()

    if args.status:
        return cmd_status()
    if args.language:
        return cmd_translate(Language(args.language), args.limit, args.batch)
    ap.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
