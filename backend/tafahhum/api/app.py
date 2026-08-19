"""HTTP surface."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from tafahhum.api.schemas import QueryIn, QueryOut, serialise
from tafahhum.core.config import get_settings
from tafahhum.core.enums import USER_LANGUAGES
from tafahhum.db.pool import connection, get_pool
from tafahhum.pipeline import QueryRequest, run_query
from tafahhum.quran.reference import parse_ayah_references


@asynccontextmanager
async def lifespan(app: FastAPI):
    get_pool()
    yield
    get_pool().close()


app = FastAPI(
    title="Tafahhum",
    description="A research platform for the historical tradition of Quranic interpretation.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

API = "/api/v1"


@app.get(f"{API}/health")
def health() -> dict:
    with connection() as conn, conn.cursor() as cur:
        cur.execute("SELECT count(*) AS n FROM published_passage")
        passages = cur.fetchone()["n"]
        cur.execute("SELECT count(*) AS n FROM tafsir_work WHERE corpus_state='PUBLISHED'")
        works = cur.fetchone()["n"]
    return {
        "status": "ok",
        "published_passages": passages,
        "published_works": works,
        "pivot_language": get_settings().pivot_language.value,
        "user_languages": [lang.value for lang in USER_LANGUAGES],
    }


@app.post(f"{API}/query", response_model=QueryOut)
def query(payload: QueryIn) -> QueryOut:
    """Run the full retrieval pipeline and return the evidence package.

    The response is evidence, not prose. A generated answer is a separate,
    downstream concern that consumes exactly this payload and nothing else.
    """
    with connection() as conn:
        package = run_query(
            conn,
            QueryRequest(
                text=payload.query,
                user_language=payload.language,
                limit=payload.limit,
                work_slugs=payload.works,
            ),
        )
    return serialise(package)


@app.get(f"{API}/rules")
def rules(active_only: bool = True) -> dict:
    """The full rule set with provenance.

    Exposed so that no rule is hidden: a user can audit exactly which rules can
    influence retrieval and what each one is grounded in.
    """
    with connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT rule_key, name, description, tier::text AS tier, priority,
                   source_book, source_reference,
                   verification_status::text AS verification_status,
                   verified_by, is_active,
                   applies_to_query_types::text[] AS applies_to
            FROM scholarly_rule
            WHERE (%s = false OR is_active)
            ORDER BY
                array_position(
                    ARRAY['SYSTEM_INTEGRITY','SOURCE_PROVENANCE','SCHOLARLY_METHOD',
                          'QUERY_STRATEGY','EVIDENCE_QUALITY','RESPONSE_STRUCTURE',
                          'LANGUAGE_GENERATION']::text[], tier::text),
                priority
            """,
            (active_only,),
        )
        rows = cur.fetchall()

    scholarly = [r for r in rows if r["source_book"] != "TAFAHHUM_BASELINE"]
    return {
        "rules": rows,
        "counts": {
            "total": len(rows),
            "structural_baseline": len(rows) - len(scholarly),
            "scholarly_attributed": len(scholarly),
        },
        "note": (
            "Rules attributed to a scholarly source appear under "
            "'scholarly_attributed'. A count of zero means no bibliographical "
            "source has yet been ingested and verified, and the engine is running "
            "on structural rules that make no scholarly claim."
        ),
    }


@app.get(f"{API}/works")
def works() -> dict:
    """The corpus catalogue."""
    with connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT w.slug, w.title_ar, w.title_en, w.corpus_state::text AS corpus_state,
                   w.verification_status::text AS verification_status,
                   m.name_ar AS author_ar, m.name_en AS author_en,
                   m.death_year_hijri,
                   count(p.id) AS passage_count,
                   count(DISTINCT (pa.surah_number, pa.ayah_start)) AS ayah_count
            FROM tafsir_work w
            LEFT JOIN mufassir m ON m.id = w.author_id
            LEFT JOIN passage p ON p.tafsir_work_id = w.id
            LEFT JOIN passage_ayah pa ON pa.passage_id = p.id
            GROUP BY w.slug, w.title_ar, w.title_en, w.corpus_state,
                     w.verification_status, m.name_ar, m.name_en, m.death_year_hijri
            ORDER BY count(p.id) DESC
            """
        )
        rows = cur.fetchall()
    return {"works": rows, "count": len(rows)}


@app.get(f"{API}/passages/{{passage_id}}")
def passage(passage_id: str) -> dict:
    """Full source inspection for one passage.

    Returns every text representation side by side, so a researcher can see
    exactly what was scanned, what was normalised for matching, and what a human
    approved — rather than only the rendered form.
    """
    with connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT p.id, p.raw_text, p.normalized_text, p.verified_text,
                   p.evidence_kind::text AS evidence_kind,
                   p.verification_status::text AS verification_status,
                   p.citation_precision::text AS citation_precision,
                   p.ocr_confidence, p.volume, p.page_start, p.page_end,
                   w.slug AS work_slug, w.title_ar, w.title_en,
                   m.name_ar AS author_ar, m.name_en AS author_en,
                   e.slug AS edition_slug, e.publisher, e.publication_year,
                   e.digital_source_url, e.license_note,
                   e.copyright_status::text AS copyright_status,
                   e.edition_quality_note,
                   sp.image_uri AS scan_page_uri
            FROM passage p
            JOIN tafsir_work w ON w.id = p.tafsir_work_id
            JOIN edition e ON e.id = p.edition_id
            LEFT JOIN mufassir m ON m.id = p.author_id
            LEFT JOIN scan_page sp ON sp.id = p.scan_page_id
            WHERE p.id = %s
            """,
            (passage_id,),
        )
        row = cur.fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="passage not found")

        cur.execute(
            """
            SELECT surah_number, ayah_start, ayah_end, alignment::text AS alignment,
                   confidence, verification_status::text AS verification_status
            FROM passage_ayah WHERE passage_id = %s
            ORDER BY surah_number, ayah_start
            """,
            (passage_id,),
        )
        row["ayah_alignments"] = cur.fetchall()

        cur.execute(
            """
            SELECT language::text AS language, text, translator_kind, translator_name,
                   model_name, verification_status::text AS verification_status
            FROM passage_translation WHERE passage_id = %s
            """,
            (passage_id,),
        )
        row["translations"] = cur.fetchall()

    return row


@app.get(f"{API}/ayah/{{surah}}/{{ayah}}")
def ayah(surah: int, ayah: int) -> dict:
    with connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT a.surah_number, a.ayah_number, a.text_uthmani, a.juz, a.page_madani,
                   s.name_ar, s.name_en, s.name_en_translit, s.ayah_count,
                   s.revelation_place
            FROM ayah a
            JOIN surah s ON s.number = a.surah_number
            JOIN quran_text_source q ON q.id = a.text_source_id
            WHERE q.is_default AND a.surah_number = %s AND a.ayah_number = %s
            """,
            (surah, ayah),
        )
        row = cur.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail=f"{surah}:{ayah} not in the corpus")
    return row


@app.get(f"{API}/parse")
def parse(q: str = Query(min_length=1)) -> dict:
    """Expose reference parsing on its own, for debugging and for the UI."""
    result = parse_ayah_references(q)
    return {
        "query": q,
        "references": [
            {"reference": str(r), "surah": r.surah, "start": r.start, "end": r.end,
             "label_en": r.label("en"), "label_ar": r.label("ar")}
            for r in result.refs
        ],
        "residual_text": result.residual_text,
    }
