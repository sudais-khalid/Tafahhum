"""Ingest Nayl al-Sairin fi Tabaqat al-Mufassirin.

    python scripts/ingest_nayl.py --survey            # inspect the PDF only
    python scripts/ingest_nayl.py --extract           # render pages, register them
    python scripts/ingest_nayl.py --ocr --engine tesseract [--pages 30-35]
    python scripts/ingest_nayl.py --ocr --engine vision --batch

The scanned copy is lithographed Urdu Nastaliq at roughly 70 DPI. Tesseract
recovers function words and mangles proper names, which is the opposite of what a
tabaqat work is read for. The vision engine handles the script but needs
credentials. Either way, nothing here produces citable text: every page lands in
HUMAN_REVIEW and no claim may be attributed to this work until a reviewer has
approved the page against its image.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import psycopg

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from tafahhum.arabic.normalize import normalize_for_matching  # noqa: E402
from tafahhum.core.config import get_settings  # noqa: E402
from tafahhum.core.enums import CorpusStatus, Language, VerificationStatus  # noqa: E402
from tafahhum.corpus.ocr import OcrResult, TesseractEngine, VisionOcrEngine  # noqa: E402
from tafahhum.corpus import pdf as pdfmod  # noqa: E402

PDF = ROOT / "data" / "seed" / "tafsir" / "Nayl us Sayireen fi Tabaqat al-Mufassireen.pdf"
SCANS = ROOT / "data" / "scans" / "nayl-al-sairin"
SLUG = "nayl-al-sairin"
PAGE_LANGUAGE = Language.UR


def biblio_id(conn: psycopg.Connection) -> str:
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM biblio_source WHERE slug = %s", (SLUG,))
        row = cur.fetchone()
        if row is None:
            raise SystemExit(f"{SLUG} not registered; run migrations first")
        return row[0] if isinstance(row, tuple) else row["id"]


def cmd_survey() -> int:
    if not PDF.exists():
        raise SystemExit(f"missing {PDF}")
    s = pdfmod.survey(PDF)
    print(f"pages              : {s.page_count}")
    print(f"text layer         : {'yes' if s.has_text_layer else 'no (OCR required)'}")
    print(f"chars sampled      : {s.text_chars_sampled}")
    print(f"median native DPI  : {s.median_native_dpi:.0f}")
    print(f"producer           : {s.producer}")
    if s.dpi_is_marginal:
        print()
        print("  The scan is below ~150 DPI. Glyph-segmenting OCR (Tesseract)")
        print("  degrades sharply on Arabic-script text at this resolution, and")
        print("  Nastaliq is the hardest case. Prefer --engine vision, or obtain")
        print("  a higher-resolution scan.")
    return 0


def cmd_extract(limit: int | None) -> int:
    settings = get_settings()
    pages = pdfmod.extract_pages(PDF, SCANS, render_dpi=300, last=limit)
    print(f"rendered {len(pages)} pages into {SCANS.relative_to(ROOT)}")

    with psycopg.connect(settings.dsn) as conn:
        source_id = biblio_id(conn)
        with conn.cursor() as cur:
            for p in pages:
                cur.execute(
                    """
                    INSERT INTO scan_page
                        (biblio_source_id, volume, page_label, page_number, image_index,
                         image_uri, image_width, image_height, image_sha256,
                         language, script, needs_review, verification_status)
                    VALUES (%s, 1, %s, %s, %s, %s, %s, %s, %s, %s, %s, true, %s)
                    -- The unique index is partial, so its predicate has to be
                    -- restated here for the conflict target to match it.
                    ON CONFLICT (biblio_source_id, volume, image_index)
                        WHERE biblio_source_id IS NOT NULL
                    DO UPDATE SET image_uri = EXCLUDED.image_uri,
                                  image_sha256 = EXCLUDED.image_sha256
                    """,
                    (
                        source_id,
                        str(p.index + 1),
                        p.index + 1,
                        p.index,
                        str(p.path.relative_to(ROOT)).replace("\\", "/"),
                        p.width,
                        p.height,
                        p.sha256,
                        PAGE_LANGUAGE.value,
                        "nastaliq",
                        VerificationStatus.UNVERIFIED.value,
                    ),
                )
        conn.commit()
    print(f"registered {len(pages)} scan pages")
    return 0


def parse_range(spec: str | None) -> tuple[int, int] | None:
    if not spec:
        return None
    if "-" in spec:
        a, b = spec.split("-", 1)
        return int(a), int(b)
    n = int(spec)
    return n, n


def store_ocr(conn: psycopg.Connection, page_id: str, result: OcrResult) -> None:
    """Write OCR output. Raw text is written once and never overwritten."""
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE scan_page SET
                ocr_raw_text = COALESCE(ocr_raw_text, %s),
                ocr_normalized_text = %s,
                ocr_engine = %s,
                ocr_engine_version = %s,
                ocr_confidence = %s,
                ocr_engine_note = %s,
                ocr_run_at = now(),
                needs_review = true,
                verification_status = %s
            WHERE id = %s
            """,
            (
                result.text,
                normalize_for_matching(result.text),
                result.engine,
                result.engine_version,
                result.confidence,
                result.note,
                VerificationStatus.MACHINE_PROPOSED.value,
                page_id,
            ),
        )


def cmd_ocr(engine_name: str, page_spec: str | None, use_batch: bool) -> int:
    settings = get_settings()
    engine = TesseractEngine() if engine_name == "tesseract" else VisionOcrEngine()

    if not engine.available():
        if engine_name == "vision":
            print(
                "The vision engine needs Anthropic credentials.\n"
                "  Run `ant auth login`, or export ANTHROPIC_API_KEY.\n"
                "  Then: python scripts/ingest_nayl.py --ocr --engine vision --batch",
                file=sys.stderr,
            )
        else:
            print("tesseract not found on PATH", file=sys.stderr)
        return 2

    rng = parse_range(page_spec)

    with psycopg.connect(settings.dsn, row_factory=psycopg.rows.dict_row) as conn:
        source_id = biblio_id(conn)
        with conn.cursor() as cur:
            if rng:
                cur.execute(
                    """SELECT id, page_number, image_uri FROM scan_page
                       WHERE biblio_source_id = %s AND page_number BETWEEN %s AND %s
                       ORDER BY page_number""",
                    (source_id, rng[0], rng[1]),
                )
            else:
                cur.execute(
                    """SELECT id, page_number, image_uri FROM scan_page
                       WHERE biblio_source_id = %s AND ocr_raw_text IS NULL
                       ORDER BY page_number""",
                    (source_id,),
                )
            pages = cur.fetchall()

        if not pages:
            print("no pages pending OCR")
            return 0

        print(f"{len(pages)} page(s) to read with {engine.name}")

        if use_batch and isinstance(engine, VisionOcrEngine):
            return _run_batch(conn, engine, pages)

        done = 0
        for row in pages:
            path = ROOT / row["image_uri"]
            if not path.exists():
                print(f"  ! missing image {path}", file=sys.stderr)
                continue
            result = engine.read_page(path, language=PAGE_LANGUAGE)
            store_ocr(conn, row["id"], result)
            conn.commit()
            done += 1
            conf = f"{result.confidence:.2f}" if result.confidence is not None else "n/a"
            print(f"  p{row['page_number']:>4}  {len(result.text):>5} chars  conf={conf}")
        print(f"read {done} page(s); all flagged for human review")
    return 0


def _run_batch(conn: psycopg.Connection, engine: VisionOcrEngine, pages: list[dict]) -> int:
    """Submit every pending page as one batch, then store the results."""
    import time

    items = [(str(r["id"]), ROOT / r["image_uri"]) for r in pages if (ROOT / r["image_uri"]).exists()]
    requests = engine.build_batch_requests(items, language=PAGE_LANGUAGE)

    batch = engine.client.messages.batches.create(requests=requests)
    print(f"batch {batch.id} submitted with {len(requests)} pages")
    print("batches usually finish within the hour; results are kept for 29 days")

    while True:
        batch = engine.client.messages.batches.retrieve(batch.id)
        if batch.processing_status == "ended":
            break
        print(f"  {batch.processing_status}: {batch.request_counts.processing} processing")
        time.sleep(30)

    stored = failed = 0
    for result in engine.client.messages.batches.results(batch.id):
        if result.result.type != "succeeded":
            failed += 1
            continue
        msg = result.result.message
        text = "".join(b.text for b in msg.content if b.type == "text").strip()
        store_ocr(
            conn,
            result.custom_id,
            OcrResult(
                text=text, engine=engine.name, engine_version=engine.model,
                confidence=None, language=PAGE_LANGUAGE,
                note="Machine transcription via batch. Requires human review.",
            ),
        )
        stored += 1
    conn.commit()
    print(f"stored {stored} page(s), {failed} failed; all flagged for human review")
    return 0


def cmd_status() -> int:
    settings = get_settings()
    with psycopg.connect(settings.dsn, row_factory=psycopg.rows.dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT count(*) AS pages,
                       count(ocr_raw_text) AS ocr_done,
                       count(ocr_verified_text) AS verified,
                       count(*) FILTER (WHERE needs_review) AS pending_review
                FROM scan_page sp
                JOIN biblio_source b ON b.id = sp.biblio_source_id
                WHERE b.slug = %s
                """,
                (SLUG,),
            )
            r = cur.fetchone()
    print(f"pages registered : {r['pages']}")
    print(f"OCR complete     : {r['ocr_done']}")
    print(f"human verified   : {r['verified']}")
    print(f"pending review   : {r['pending_review']}")
    if r["verified"] == 0 and r["ocr_done"]:
        print()
        print("  No page has been verified, so no claim may yet be attributed to")
        print("  this work. Machine transcription is a proposal, not a source.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--survey", action="store_true")
    ap.add_argument("--extract", action="store_true")
    ap.add_argument("--ocr", action="store_true")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--engine", choices=["tesseract", "vision"], default="vision")
    ap.add_argument("--pages", help="page or range, e.g. 31 or 30-40")
    ap.add_argument("--limit", type=int, help="only extract the first N pages")
    ap.add_argument("--batch", action="store_true", help="use the Batches API")
    args = ap.parse_args()

    if args.survey:
        return cmd_survey()
    if args.extract:
        return cmd_extract(args.limit)
    if args.ocr:
        return cmd_ocr(args.engine, args.pages, args.batch)
    if args.status:
        return cmd_status()
    ap.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
