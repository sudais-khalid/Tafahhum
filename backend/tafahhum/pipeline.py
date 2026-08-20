"""The query pipeline.

    detect language → pivot to Arabic → resolve ayahs → classify
      → load rules → plan → retrieve → fuse → assemble evidence → log

Everything above the evidence package is retrieval. Everything below it is
presentation. The two never touch, which is what keeps the response layer
replaceable and keeps it from reaching back into the corpus.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

import psycopg

from tafahhum.core.config import get_settings
from tafahhum.core.enums import Language
from tafahhum.evidence.assemble import EvidencePackage, assemble
from tafahhum.language.detect import detect_language
from tafahhum.language.pivot import to_pivot
from tafahhum.retrieval.search import hybrid_search
from tafahhum.rules.classify import classify
from tafahhum.rules.engine import plan_for


@dataclass(frozen=True)
class QueryRequest:
    text: str
    user_language: Language | None = None
    limit: int | None = None
    work_slugs: list[str] | None = None


def load_work_terms(conn: psycopg.Connection) -> dict[str, str]:
    """Searchable name fragments for every published work, mapped to its slug.

    Built from the corpus rather than hardcoded, so naming a Mufassir is
    recognised exactly when that Mufassir is actually indexed.
    """
    from tafahhum.arabic.normalize import normalize_key

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT w.slug, w.title_ar, w.title_en, w.short_name,
                   m.name_ar, m.name_en
            FROM tafsir_work w
            LEFT JOIN mufassir m ON m.id = w.author_id
            WHERE w.corpus_state = 'PUBLISHED'
            """
        )
        rows = cur.fetchall()

    terms: dict[str, str] = {}
    for r in rows:
        # The distinguishing part of a name is its nisba — "al-Tabari", not
        # "Muhammad ibn Jarir", which it shares with many others. Index the
        # trailing element of the English name plus the full Arabic name.
        if r["name_en"]:
            last = r["name_en"].split()[-1].lower().replace("al-", "")
            if len(last) >= 4:
                terms.setdefault(last, r["slug"])
        for value in (r["name_ar"], r["title_ar"], r["short_name"]):
            if value:
                key = normalize_key(value)
                if len(key) >= 4:
                    terms.setdefault(key, r["slug"])
    return terms


def run_query(conn: psycopg.Connection, request: QueryRequest) -> EvidencePackage:
    """Execute the full pipeline for one query."""
    settings = get_settings()
    started = time.perf_counter()

    # 1. Language
    default_lang = request.user_language or settings.default_user_language
    detection = detect_language(request.text, default=default_lang)
    user_language = request.user_language or detection.language

    # 2. Pivot into Arabic — the corpus language
    pivot = to_pivot(request.text, source=detection.language)

    # 3. Classify against the actual corpus
    work_terms = load_work_terms(conn)
    classification = classify(request.text, known_work_terms=work_terms)

    # A query that named works explicitly narrows retrieval to them.
    work_slugs = request.work_slugs
    if not work_slugs and classification.named_works:
        work_slugs = classification.named_works

    # 4. Rules
    plan = plan_for(conn, classification.query_type)

    # 5. Retrieve. The Arabic pivot text is what reaches the index; the residual
    #    English or Urdu wording would not match an Arabic corpus.
    search_text = pivot.pivot_text if pivot.pivot_text.strip() else classification.residual_text
    passages, trace = hybrid_search(
        conn,
        refs=classification.refs,
        query_text=search_text,
        work_slugs=work_slugs,
        limit=request.limit or settings.evidence_limit,
        per_work=plan.per_work_cap,
    )
    trace.rules_applied = [r.rule_key for r in plan.applied_rules]

    # 6. Assemble
    package = assemble(
        conn,
        query=request.text,
        user_language=user_language,
        pivot_query=pivot.pivot_text,
        classification=classification,
        plan=plan,
        passages=passages,
        trace=trace,
    )
    if pivot.note:
        package.notes.append(pivot.note)

    duration_ms = int((time.perf_counter() - started) * 1000)
    _log_run(conn, request, detection, classification, package, duration_ms)
    return package


def _log_run(
    conn: psycopg.Connection,
    request: QueryRequest,
    detection,
    classification,
    package: EvidencePackage,
    duration_ms: int,
) -> None:
    """Record the run and the rules that fired, for the transparency panel."""
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO query_run
                    (raw_query, user_language, pivot_query, detected_language,
                     classified_type, classification_confidence, resolved_ayahs,
                     evidence_count, duration_ms)
                VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s)
                RETURNING id
                """,
                (
                    request.text,
                    package.user_language.value,
                    package.pivot_query,
                    detection.language.value,
                    classification.query_type.value,
                    classification.confidence,
                    '[' + ",".join(f'"{r}"' for r in map(str, classification.refs)) + ']',
                    package.passage_count,
                    duration_ms,
                ),
            )
            run_id = cur.fetchone()["id"]
            for rule in package.rules_applied:
                cur.execute(
                    """
                    INSERT INTO query_run_rule (query_run_id, rule_id, applied_at_stage)
                    SELECT %s, id, 'retrieval' FROM scholarly_rule WHERE rule_key = %s
                    ON CONFLICT DO NOTHING
                    """,
                    (run_id, rule["rule"]),
                )
        conn.commit()
    except psycopg.Error:
        # Audit logging must never take down a query. The run is lost from the
        # log, not from the user.
        conn.rollback()
