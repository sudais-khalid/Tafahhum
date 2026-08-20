"""HTTP surface."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from tafahhum.api.reading import build_reading
from tafahhum.api.schemas import QueryIn, QueryOut, serialise
from tafahhum.core.config import get_settings
from tafahhum.core.enums import USER_LANGUAGES, Language
from tafahhum.db.pool import connection, get_pool
from tafahhum.language.translate import translate_passage
from tafahhum.pipeline import QueryRequest, run_query
from tafahhum.quran.reference import parse_ayah_references

REPO_ROOT = Path(__file__).resolve().parents[3]
SCAN_ROOT = (REPO_ROOT / "data" / "scans").resolve()


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
        work_slugs = payload.works
        # An explicit list of works is a more specific instruction than a preset,
        # so it wins; a preset only fills in when nothing was named.
        if not work_slugs and payload.preset:
            preset = next((p for p in PRESETS if p["key"] == payload.preset), None)
            if preset is None:
                raise HTTPException(
                    status_code=400,
                    detail=f"unknown preset {payload.preset!r}; see GET {API}/catalogue",
                )
            with conn.cursor() as cur:
                work_slugs = _resolve_preset(cur, preset)

        package = run_query(
            conn,
            QueryRequest(
                text=payload.query,
                user_language=payload.language,
                limit=payload.limit,
                work_slugs=work_slugs,
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


@app.post(f"{API}/passages/{{passage_id}}/translate")
def translate(passage_id: str, language: Language = Query()) -> dict:
    """Translate one passage into a user language.

    The response deliberately carries the source text alongside the translation
    and flags whether the translation is machine-produced, so a client cannot
    render the translation without also having the original and its provenance.
    """
    if language not in USER_LANGUAGES:
        raise HTTPException(
            status_code=400,
            detail=f"language must be one of {[lang.value for lang in USER_LANGUAGES]}",
        )

    with connection() as conn:
        translation, status = translate_passage(conn, passage_id, target=language)

        if status == "not_found":
            raise HTTPException(status_code=404, detail="passage not found")
        if status == "unavailable":
            raise HTTPException(
                status_code=503,
                detail=(
                    "No translation backend is configured. Set ANTHROPIC_API_KEY "
                    "or run `ant auth login` on the server, then retry."
                ),
            )

        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT COALESCE(p.verified_text, p.raw_text) AS source_text,
                       p.language::text AS source_language
                FROM passage p WHERE p.id = %s
                """,
                (passage_id,),
            )
            src = cur.fetchone()

    assert translation is not None
    return {
        "passage_id": passage_id,
        "language": translation.language.value,
        "text": translation.text,
        "source_text": src["source_text"],
        "source_language": src["source_language"],
        "translator_kind": translation.translator_kind,
        "translator_name": translation.translator_name,
        "model_name": translation.model_name,
        "verification_status": translation.verification_status.value,
        "is_machine_translation": translation.is_machine,
        "cached": status == "cached",
        # Empty text with a note means the attempt was made and rejected — a
        # degenerate local model, or a failed call. The client must be able to
        # tell that apart from "not tried yet".
        "attempted": True,
        "note": translation.note,
        "notice": (
            "This is a translation, not the source. The original is shown beside "
            "it and is what citations refer to."
        ),
    }


# Curated starting points. Fifty works is too many to choose between from a
# cold start, and "pick your sources" is only a real choice if the options mean
# something to someone who is not already a specialist. Each preset is a query
# over catalogue metadata, not a hand-maintained list, so it stays correct as
# works are added.
PRESETS: list[dict] = [
    {
        "key": "sunni-core",
        "name_en": "Sunni core",
        "name_ar": "الأمهات السنية",
        "name_ur": "بنیادی سنی تفاسیر",
        "description_en": "Widely-cited works a named reference classifies as Sunni.",
        "traditions": ["SUNNI", "SUNNI_SUFI", "SUNNI_SALAFI"],
        "default_only": True,
    },
    {
        "key": "sunni-all",
        "name_en": "All Sunni works",
        "name_ar": "جميع التفاسير السنية",
        "name_ur": "تمام سنی تفاسیر",
        "description_en": "Every indexed work classified under a Sunni heading.",
        "traditions": ["SUNNI", "SUNNI_SUFI", "SUNNI_SALAFI"],
    },
    {
        "key": "mathur",
        "name_en": "Transmitted reports",
        "name_ar": "التفسير بالمأثور",
        "name_ur": "تفسیر بالمأثور",
        "description_en": "Commentary built on transmitted reports and chains.",
        "methods": ["BI_AL_MATHUR"],
    },
    {
        "key": "fiqhi",
        "name_en": "Legal commentary",
        "name_ar": "أحكام القرآن",
        "name_ur": "احکام القرآن",
        "description_en": "Works focused on legal rulings drawn from the text.",
        "methods": ["FIQHI"],
    },
    {
        "key": "lughawi",
        "name_en": "Language and rhetoric",
        "name_ar": "اللغة والبلاغة",
        "name_ur": "لغت و بلاغت",
        "description_en": "Grammatical, syntactic, and rhetorical analysis.",
        "methods": ["LUGHAWI", "BALAGHI", "GHARIB"],
    },
    {
        "key": "qiraat",
        "name_en": "Variant readings",
        "name_ar": "القراءات",
        "name_ur": "قراءات",
        "description_en": "Works on the variant readings of the text.",
        "methods": ["QIRAAT"],
    },
    {
        "key": "commentaries",
        "name_en": "All commentaries",
        "name_ar": "جميع التفاسير",
        "name_ur": "تمام تفاسیر",
        "description_en": (
            "Every work that comments on meaning, excluding grammar and "
            "recitation apparatus."
        ),
        "methods": [
            "BI_AL_MATHUR", "BI_AL_RAY", "FIQHI", "BALAGHI",
            "SUFI_ISHARI", "KALAMI", "MIXED",
        ],
    },
    {
        "key": "everything",
        "name_en": "Everything indexed",
        "name_ar": "كل المفهرس",
        "name_ur": "تمام فہرست شدہ",
        "description_en": "All works, including non-Sunni and unclassified ones.",
    },
]


def _resolve_preset(cur, preset: dict) -> list[str]:
    """Turn a preset into the work slugs it currently selects."""
    clauses = ["corpus_state = 'PUBLISHED'"]
    params: list[object] = []
    if preset.get("traditions"):
        clauses.append("tradition::text = ANY(%s)")
        params.append(preset["traditions"])
    if preset.get("methods"):
        clauses.append("method::text = ANY(%s)")
        params.append(preset["methods"])
    if preset.get("default_only"):
        clauses.append("is_default_source")
    cur.execute(
        f"SELECT slug FROM tafsir_work WHERE {' AND '.join(clauses)} "
        f"ORDER BY catalogue_rank, slug",
        params,
    )
    return [r["slug"] for r in cur.fetchall()]


@app.get(f"{API}/read/{{surah}}/{{ayah}}")
def read(
    surah: int,
    ayah: int,
    language: Language = Query(default=Language.EN),
    works: str | None = Query(default=None, description="Comma-separated work slugs"),
    preset: str | None = Query(default=None),
) -> dict:
    """One ayah, organised clause by clause for reading.

    The counterpart to /query: same corpus, same provenance, arranged for
    someone learning the ayah rather than auditing the evidence.
    """
    slugs = [s.strip() for s in works.split(",") if s.strip()] if works else None

    with connection() as conn:
        if not slugs and preset:
            chosen = next((p for p in PRESETS if p["key"] == preset), None)
            if chosen is None:
                raise HTTPException(status_code=400, detail=f"unknown preset {preset!r}")
            with conn.cursor() as cur:
                slugs = _resolve_preset(cur, chosen)

        result = build_reading(
            conn, surah=surah, ayah=ayah, language=language, work_slugs=slugs
        )

    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"{surah}:{ayah} is not in the corpus yet",
        )
    return result


@app.get(f"{API}/catalogue")
def catalogue() -> dict:
    """The selectable corpus, with classification and its provenance.

    Classification is reported with the source that made it and its verification
    state, so a reader filtering by school can see that they are filtering on a
    tertiary reference rather than on Tafahhum's judgement.
    """
    with connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT w.slug, w.title_ar, w.title_en,
                   w.tradition::text AS tradition, w.method::text AS method,
                   w.classification_source, w.classification_source_url,
                   w.classification_status::text AS classification_status,
                   w.classification_note, w.catalogue_rank, w.is_default_source,
                   m.name_ar AS author_ar, m.name_en AS author_en,
                   m.death_year_hijri, m.period::text AS period,
                   count(p.id) AS passage_count,
                   count(DISTINCT (pa.surah_number, pa.ayah_start)) AS ayah_count
            FROM tafsir_work w
            LEFT JOIN mufassir m ON m.id = w.author_id
            LEFT JOIN passage p ON p.tafsir_work_id = w.id
            LEFT JOIN passage_ayah pa ON pa.passage_id = p.id
            WHERE w.corpus_state = 'PUBLISHED'
            GROUP BY w.slug, w.title_ar, w.title_en, w.tradition, w.method,
                     w.classification_source, w.classification_source_url,
                     w.classification_status, w.classification_note,
                     w.catalogue_rank, w.is_default_source,
                     m.name_ar, m.name_en, m.death_year_hijri, m.period
            ORDER BY w.catalogue_rank, w.slug
            """
        )
        works = cur.fetchall()

        presets = []
        for preset in PRESETS:
            slugs = _resolve_preset(cur, preset)
            presets.append({**preset, "work_slugs": slugs, "work_count": len(slugs)})

    by_tradition: dict[str, int] = {}
    for w in works:
        by_tradition[w["tradition"]] = by_tradition.get(w["tradition"], 0) + 1

    return {
        "works": works,
        "presets": presets,
        "counts": {
            "works": len(works),
            "passages": sum(w["passage_count"] for w in works),
            "by_tradition": by_tradition,
        },
        "classification_note": (
            "School and method are taken from a tertiary reference and are "
            "UNVERIFIED. Works the reference does not list are marked "
            "UNCLASSIFIED rather than assigned a school by inference."
        ),
    }


@app.get(f"{API}/biblio")
def biblio_sources() -> dict:
    """Bibliographical sources and how far their processing has got."""
    with connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT b.slug, b.title_ar, b.title_en, b.genre,
                   b.verification_status::text AS verification_status, b.notes,
                   count(sp.id) AS pages,
                   count(sp.ocr_raw_text) AS ocr_complete,
                   count(sp.ocr_verified_text) AS human_verified,
                   round(avg(sp.ocr_confidence)::numeric, 3) AS mean_ocr_confidence
            FROM biblio_source b
            LEFT JOIN scan_page sp ON sp.biblio_source_id = b.id
            GROUP BY b.slug, b.title_ar, b.title_en, b.genre,
                     b.verification_status, b.notes
            ORDER BY b.slug
            """
        )
        rows = cur.fetchall()

    for r in rows:
        r["citable"] = r["human_verified"] > 0
    return {
        "sources": rows,
        "note": (
            "A source becomes citable only once pages have been verified by a "
            "human against the page image. Machine transcription is a proposal."
        ),
    }


@app.get(f"{API}/scans/{{scan_page_id}}")
def scan_page(scan_page_id: str) -> dict:
    """One scanned page with its OCR state, for the review interface."""
    with connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT sp.id, sp.page_number, sp.page_label, sp.volume, sp.image_uri,
                   sp.image_width, sp.image_height, sp.language::text AS language,
                   sp.script, sp.ocr_raw_text, sp.ocr_normalized_text,
                   sp.ocr_verified_text, sp.ocr_engine, sp.ocr_engine_version,
                   sp.ocr_confidence, sp.ocr_engine_note, sp.needs_review,
                   sp.verification_status::text AS verification_status,
                   sp.reviewed_by, sp.reviewed_at,
                   b.slug AS source_slug, b.title_ar AS source_title
            FROM scan_page sp
            LEFT JOIN biblio_source b ON b.id = sp.biblio_source_id
            WHERE sp.id = %s
            """,
            (scan_page_id,),
        )
        row = cur.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="scan page not found")
    return row


@app.get(f"{API}/scans/{{scan_page_id}}/image")
def scan_image(scan_page_id: str) -> FileResponse:
    """Serve the page image — the primary evidence behind any citation."""
    with connection() as conn, conn.cursor() as cur:
        cur.execute("SELECT image_uri FROM scan_page WHERE id = %s", (scan_page_id,))
        row = cur.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="scan page not found")

    path = (REPO_ROOT / row["image_uri"]).resolve()
    # Confine reads to the scan directory: image_uri is data, and a path that
    # escaped it would turn this endpoint into an arbitrary file read.
    if not path.is_file() or not path.is_relative_to(SCAN_ROOT):
        raise HTTPException(status_code=404, detail="image not available")
    return FileResponse(path, media_type="image/png")


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
