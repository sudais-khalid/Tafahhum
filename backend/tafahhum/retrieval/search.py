"""Retrieval strategies and their fusion.

Three strategies, run independently and fused:

  structural  — passages aligned to a queried ayah. Exact, and the backbone of
                any ayah-scoped question.
  sparse      — PostgreSQL full-text search over normalised Arabic. Catches exact
                phrasing, names, technical terms, and quotations.
  dense       — vector similarity, for questions whose wording does not appear in
                the text ("divine forgiveness" against passages using other terms).

Dense retrieval is only run when embeddings exist; the system degrades to
structural + sparse rather than failing, because an un-embedded corpus is a normal
state during ingestion.

Fusion is Reciprocal Rank Fusion. Scores from a tsvector rank and a cosine
distance are not comparable — they have different scales and distributions — so
fusing on rank rather than score avoids inventing a common scale that does not
exist.
"""

from __future__ import annotations

import psycopg

from tafahhum.arabic.normalize import normalize_for_matching
from tafahhum.core.config import get_settings
from tafahhum.core.enums import EvidenceType, Language, VerificationStatus
from tafahhum.quran.reference import AyahRef
from tafahhum.retrieval.models import Citation, RetrievalTrace, RetrievedPassage

# Every retrieval query selects this projection, so a citation is always complete.
_PROJECTION = """
    p.id                    AS passage_id,
    p.raw_text              AS raw_text,
    p.verified_text         AS verified_text,
    p.normalized_text       AS normalized_text,
    p.evidence_kind         AS evidence_kind,
    p.language              AS passage_language,
    p.verification_status   AS verification_status,
    p.citation_precision    AS citation_precision,
    p.volume                AS volume,
    p.page_start            AS page_start,
    p.page_end              AS page_end,
    w.slug                  AS work_slug,
    w.title_ar              AS work_title_ar,
    w.title_en              AS work_title_en,
    m.name_ar               AS author_name_ar,
    m.name_en               AS author_name_en,
    m.death_year_hijri      AS author_death_year_hijri,
    e.slug                  AS edition_slug,
    e.publisher             AS edition_publisher,
    e.publication_year      AS edition_year,
    e.digital_source_url    AS edition_source_url,
    e.copyright_status      AS edition_copyright_status,
    e.license_note          AS edition_license_note,
    e.verification_status   AS edition_verification_status,
    sp.image_uri            AS scan_page_uri,
    pa.surah_number         AS surah_number,
    pa.ayah_start           AS ayah_start,
    pa.ayah_end             AS ayah_end,
    pa.confidence           AS ayah_confidence
"""

_JOINS = """
    FROM published_passage p
    JOIN tafsir_work w ON w.id = p.tafsir_work_id
    JOIN edition e     ON e.id = p.edition_id
    LEFT JOIN mufassir m  ON m.id = p.author_id
    LEFT JOIN scan_page sp ON sp.id = p.scan_page_id
    LEFT JOIN passage_ayah pa ON pa.passage_id = p.id
"""


def _to_passage(row: dict) -> RetrievedPassage:
    citation = Citation(
        passage_id=str(row["passage_id"]),
        work_slug=row["work_slug"],
        work_title_ar=row["work_title_ar"],
        work_title_en=row["work_title_en"],
        author_name_ar=row["author_name_ar"] or "—",
        author_name_en=row["author_name_en"],
        author_death_year_hijri=row["author_death_year_hijri"],
        edition_slug=row["edition_slug"],
        edition_publisher=row["edition_publisher"],
        edition_year=row["edition_year"],
        edition_source_url=row["edition_source_url"],
        edition_copyright_status=row["edition_copyright_status"],
        edition_license_note=row["edition_license_note"],
        edition_verification_status=VerificationStatus(row["edition_verification_status"]),
        volume=row["volume"],
        page_start=row["page_start"],
        page_end=row["page_end"],
        scan_page_uri=row["scan_page_uri"],
        citation_precision=VerificationStatus(row["citation_precision"]),
    )
    return RetrievedPassage(
        citation=citation,
        # Display prefers the human-verified reading, never the normalised form.
        display_text=row["verified_text"] or row["raw_text"],
        normalized_text=row["normalized_text"],
        language=Language(row["passage_language"]),
        evidence_kind=EvidenceType(row["evidence_kind"]),
        verification_status=VerificationStatus(row["verification_status"]),
        surah_number=row["surah_number"],
        ayah_start=row["ayah_start"],
        ayah_end=row["ayah_end"],
        ayah_alignment_confidence=row["ayah_confidence"],
    )


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

def search_structural(
    conn: psycopg.Connection,
    refs: list[AyahRef],
    *,
    work_slugs: list[str] | None = None,
    per_work_limit: int = 6,
    limit: int = 200,
) -> list[RetrievedPassage]:
    """Passages aligned to any of the queried ayahs, retrieved per work.

    Uses range overlap, so a passage covering 2:255-257 is found by a query for
    2:256 — which a start/end equality test would miss.

    The per-work partition is the important part. A long commentary produces far
    more passages on an ayah than a terse one — al-Razi gives 501 passages across
    the seeded ayahs where al-Jalalayn gives 21 — so an undifferentiated
    ``ORDER BY`` fills the entire result set with whichever Mufassir wrote at
    greatest length. Ranking within each work first makes retrieval independent
    per source, which is what a comparative question requires.

    Passages are ranked within a work by reading order, so the opening of a
    commentary on an ayah outranks a digression later in the same discussion.
    """
    if not refs:
        return []

    conditions = []
    params: list[object] = []
    for ref in refs:
        conditions.append(
            "(pa.surah_number = %s AND int4range(pa.ayah_start, pa.ayah_end, '[]') "
            "&& int4range(%s, %s, '[]'))"
        )
        params.extend([ref.surah, ref.start, ref.end])

    where = f"({' OR '.join(conditions)})"
    if work_slugs:
        where += " AND w.slug = ANY(%s)"
        params.append(work_slugs)

    sql = f"""
        WITH ranked AS (
            SELECT {_PROJECTION},
                   ROW_NUMBER() OVER (
                       PARTITION BY w.slug
                       ORDER BY pa.surah_number, pa.ayah_start, p.sequence_index
                   ) AS work_rank
            {_JOINS}
            WHERE {where}
        )
        SELECT * FROM ranked
        WHERE work_rank <= %s
        ORDER BY work_rank, work_slug
        LIMIT %s
    """
    params.extend([per_work_limit, limit])

    with conn.cursor() as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()

    # Ordering by work_rank first interleaves the works, so the fused rank a
    # passage receives reflects its standing within its own commentary rather
    # than the length of that commentary.
    out = []
    for rank, row in enumerate(rows, start=1):
        p = _to_passage(row)
        p.ranks["structural"] = rank
        p.strategies.append("structural")
        out.append(p)
    return out


def search_sparse(
    conn: psycopg.Connection,
    query_text: str,
    *,
    refs: list[AyahRef] | None = None,
    work_slugs: list[str] | None = None,
    limit: int | None = None,
) -> list[RetrievedPassage]:
    """Full-text search over the normalised Arabic index.

    The query must be normalised with the *same* pipeline as the index, or the
    two never meet: the index stores "معني" (the matching form) while a user
    types "معنى" with alef maqsura, and an un-normalised query silently returns
    nothing rather than failing loudly.
    """
    if not query_text or not query_text.strip():
        return []

    normalized_query = normalize_for_matching(query_text)
    if not normalized_query.strip():
        return []

    settings = get_settings()
    limit = limit or settings.sparse_candidate_limit

    params: list[object] = [normalized_query]
    where = ["p.search_vector @@ q"]

    if refs:
        ors = []
        for ref in refs:
            ors.append(
                "(pa.surah_number = %s AND int4range(pa.ayah_start, pa.ayah_end, '[]') "
                "&& int4range(%s, %s, '[]'))"
            )
            params.extend([ref.surah, ref.start, ref.end])
        where.append(f"({' OR '.join(ors)})")

    if work_slugs:
        where.append("w.slug = ANY(%s)")
        params.append(work_slugs)

    sql = f"""
        SELECT {_PROJECTION}, ts_rank(p.search_vector, q) AS score
        {_JOINS},
        LATERAL websearch_to_tsquery('tafahhum_ar', %s) q
        WHERE {' AND '.join(where)}
        ORDER BY score DESC
        LIMIT %s
    """
    params.append(limit)

    with conn.cursor() as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()

    out = []
    for rank, row in enumerate(rows, start=1):
        p = _to_passage(row)
        p.ranks["sparse"] = rank
        p.scores["sparse"] = float(row["score"])
        p.strategies.append("sparse")
        out.append(p)
    return out


def search_dense(
    conn: psycopg.Connection,
    embedding: list[float] | None,
    *,
    refs: list[AyahRef] | None = None,
    work_slugs: list[str] | None = None,
    limit: int | None = None,
) -> list[RetrievedPassage]:
    """Vector similarity search. Returns nothing when the corpus is un-embedded."""
    if embedding is None:
        return []

    settings = get_settings()
    limit = limit or settings.dense_candidate_limit

    params: list[object] = [str(embedding)]
    where = ["p.embedding IS NOT NULL"]

    if refs:
        ors = []
        for ref in refs:
            ors.append(
                "(pa.surah_number = %s AND int4range(pa.ayah_start, pa.ayah_end, '[]') "
                "&& int4range(%s, %s, '[]'))"
            )
            params.extend([ref.surah, ref.start, ref.end])
        where.append(f"({' OR '.join(ors)})")

    if work_slugs:
        where.append("w.slug = ANY(%s)")
        params.append(work_slugs)

    sql = f"""
        SELECT {_PROJECTION}, (p.embedding <=> %s::vector) AS distance
        {_JOINS}
        WHERE {' AND '.join(where)}
        ORDER BY distance ASC
        LIMIT %s
    """
    params = [str(embedding), *params[1:], limit]

    with conn.cursor() as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()

    out = []
    for rank, row in enumerate(rows, start=1):
        p = _to_passage(row)
        p.ranks["dense"] = rank
        p.scores["dense"] = 1.0 - float(row["distance"])
        p.strategies.append("dense")
        out.append(p)
    return out


# ---------------------------------------------------------------------------
# Fusion
# ---------------------------------------------------------------------------

def reciprocal_rank_fusion(
    result_sets: dict[str, list[RetrievedPassage]],
    *,
    k: int | None = None,
    weights: dict[str, float] | None = None,
) -> list[RetrievedPassage]:
    """Fuse ranked lists by reciprocal rank.

    Each passage scores ``sum(weight / (k + rank))`` over the strategies that
    found it, so agreement between strategies is rewarded without requiring their
    scores to be on a common scale.
    """
    k = k or get_settings().rrf_k
    weights = weights or {}

    merged: dict[str, RetrievedPassage] = {}
    for strategy, results in result_sets.items():
        weight = weights.get(strategy, 1.0)
        for passage in results:
            existing = merged.get(passage.passage_id)
            if existing is None:
                merged[passage.passage_id] = passage
                existing = passage
            else:
                existing.ranks.update(passage.ranks)
                existing.scores.update(passage.scores)
                for s in passage.strategies:
                    if s not in existing.strategies:
                        existing.strategies.append(s)
            rank = passage.ranks.get(strategy)
            if rank is not None:
                existing.fused_score += weight / (k + rank)

    return sorted(merged.values(), key=lambda p: p.fused_score, reverse=True)


def diversify_by_work(
    passages: list[RetrievedPassage], *, per_work: int = 3
) -> list[RetrievedPassage]:
    """Round-robin passages across works, capped at `per_work` each.

    Fusion alone does not guarantee breadth: if one commentary is both long and
    lexically close to the query, it can occupy every slot. For a question of the
    form "what do the Tafasir say", breadth across Mufassirun *is* the answer, so
    coverage is enforced structurally rather than hoped for.

    Relative order within a work is preserved, so this changes which passages are
    shown, never which passage a work is best represented by.
    """
    by_work: dict[str, list[RetrievedPassage]] = {}
    for p in passages:
        by_work.setdefault(p.citation.work_slug, []).append(p)

    # Works are visited in order of their best-scoring passage, so the most
    # relevant commentary still leads.
    order = sorted(by_work, key=lambda slug: -by_work[slug][0].fused_score)

    out: list[RetrievedPassage] = []
    for round_index in range(per_work):
        for slug in order:
            group = by_work[slug]
            if round_index < len(group):
                out.append(group[round_index])
    return out


def hybrid_search(
    conn: psycopg.Connection,
    *,
    refs: list[AyahRef],
    query_text: str,
    embedding: list[float] | None = None,
    work_slugs: list[str] | None = None,
    limit: int | None = None,
    per_work: int = 3,
) -> tuple[list[RetrievedPassage], RetrievalTrace]:
    """Run every applicable strategy and fuse the results."""
    settings = get_settings()
    limit = limit or settings.rerank_limit
    trace = RetrievalTrace()

    result_sets: dict[str, list[RetrievedPassage]] = {}

    if refs:
        structural = search_structural(conn, refs, work_slugs=work_slugs)
        result_sets["structural"] = structural
        trace.strategies_run.append("structural")
        trace.candidates_per_strategy["structural"] = len(structural)

    if query_text.strip():
        sparse = search_sparse(conn, query_text, refs=refs or None, work_slugs=work_slugs)
        result_sets["sparse"] = sparse
        trace.strategies_run.append("sparse")
        trace.candidates_per_strategy["sparse"] = len(sparse)

    dense = search_dense(conn, embedding, refs=refs or None, work_slugs=work_slugs)
    if dense:
        result_sets["dense"] = dense
        trace.strategies_run.append("dense")
        trace.candidates_per_strategy["dense"] = len(dense)

    # Structural matching is exact where sparse and dense are approximate, so it
    # carries more weight when the query named an ayah.
    fused = reciprocal_rank_fusion(
        result_sets, weights={"structural": 1.5, "sparse": 1.0, "dense": 1.0}
    )
    trace.fused_candidates = len(fused)

    diversified = diversify_by_work(fused, per_work=per_work)
    trace.filters_applied = {
        "ayahs": [str(r) for r in refs],
        "works": work_slugs or "all",
        "published_only": settings.published_only,
        "per_work_cap": per_work,
    }

    out = diversified[:limit]
    trace.returned = len(out)
    trace.works_represented = len({p.citation.work_slug for p in out})
    return out, trace
