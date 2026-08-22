"""Fetch the Quranic text and its translations for all 114 surahs.

    python scripts/fetch_full_quran_text.py

The commentary ingester loads Tafsir for every ayah, but clause segmentation and
the reading view both need the verse itself, and a reader working in English or
Urdu needs an established translation beside it. Without those the corpus has
commentary on verses the system cannot display — which is how 5,939 ayahs came
to be silently skipped during clause derivation.

Resumable: each surah is cached on disk and skipped if already fetched.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import httpx
import psycopg

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from tafahhum.arabic.normalize import normalize_for_matching  # noqa: E402
from tafahhum.core.config import get_settings  # noqa: E402
from tafahhum.core.enums import CopyrightStatus, VerificationStatus  # noqa: E402

CACHE = ROOT / "data" / "quran" / "full"
BASE = "https://api.alquran.cloud/v1/surah"

TEXT_EDITION = "quran-uthmani"

# Two established translations per language, each by a named translator. Revealed
# text is never machine-translated.
TRANSLATIONS = [
    {"slug": "en.sahih", "lang": "en", "translator": "Saheeh International"},
    {"slug": "en.yusufali", "lang": "en", "translator": "Abdullah Yusuf Ali"},
    {"slug": "ur.jalandhry", "lang": "ur", "translator": "Fateh Muhammad Jalandhry"},
    {"slug": "ur.junagarhi", "lang": "ur", "translator": "Muhammad Junagarhi"},
]


def fetch_edition(client: httpx.Client, edition: str) -> dict[str, dict]:
    """All 114 surahs of one edition, cached whole."""
    dest = CACHE / f"{edition}.json"
    if dest.exists():
        return json.loads(dest.read_text(encoding="utf-8"))

    dest.parent.mkdir(parents=True, exist_ok=True)
    out: dict[str, dict] = {}
    for surah in range(1, 115):
        for attempt in range(3):
            try:
                r = client.get(f"{BASE}/{surah}/{edition}", timeout=60)
                r.raise_for_status()
                break
            except httpx.HTTPError:
                if attempt == 2:
                    raise
                time.sleep(2 * (attempt + 1))
        for a in r.json()["data"]["ayahs"]:
            out[f"{surah}:{a['numberInSurah']}"] = {
                "surah": surah,
                "ayah": a["numberInSurah"],
                "text": a["text"],
                "juz": a.get("juz"),
                "page": a.get("page"),
                "sajda": bool(a.get("sajda")),
            }
        if surah % 20 == 0:
            print(f"    {edition}: {surah}/114", flush=True)
        time.sleep(0.1)

    dest.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    return out


def ingest_text(conn: psycopg.Connection, ayahs: dict) -> int:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id FROM quran_text_source WHERE slug = 'hafs-uthmani'"
        )
        row = cur.fetchone()
        source_id = row[0] if row else None
        if source_id is None:
            raise SystemExit("hafs-uthmani text source missing; run fetch_corpus.py first")

        cur.executemany(
            """
            INSERT INTO ayah
                (text_source_id, surah_number, ayah_number, text_uthmani,
                 text_normalized, juz, page_madani, sajdah)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (text_source_id, surah_number, ayah_number)
            DO UPDATE SET text_uthmani = EXCLUDED.text_uthmani,
                          text_normalized = EXCLUDED.text_normalized
            """,
            [
                (
                    source_id, r["surah"], r["ayah"], r["text"],
                    normalize_for_matching(r["text"]),
                    r.get("juz"), r.get("page"), r.get("sajda", False),
                )
                for r in ayahs.values()
            ],
        )
    conn.commit()
    return len(ayahs)


def ingest_translation(conn: psycopg.Connection, edition: dict, texts: dict) -> int:
    with conn.cursor() as cur:
        cur.executemany(
            """
            INSERT INTO ayah_translation
                (surah_number, ayah_number, language, translator_name,
                 translation_slug, text, source_url, copyright_status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (translation_slug, surah_number, ayah_number)
            DO UPDATE SET text = EXCLUDED.text
            """,
            [
                (
                    r["surah"], r["ayah"], edition["lang"], edition["translator"],
                    edition["slug"], r["text"],
                    f"https://api.alquran.cloud/v1/surah/{{surah}}/{edition['slug']}",
                    CopyrightStatus.UNKNOWN.value,
                )
                for r in texts.values()
            ],
        )
    conn.commit()
    return len(texts)


def main() -> int:
    settings = get_settings()
    with httpx.Client(follow_redirects=True) as client, \
            psycopg.connect(settings.dsn) as conn:

        print("Quranic text (Hafs, Uthmani) ...")
        text = fetch_edition(client, TEXT_EDITION)
        print(f"  ingested {ingest_text(conn, text)} ayahs")

        for edition in TRANSLATIONS:
            print(f"{edition['slug']} — {edition['translator']} ...")
            texts = fetch_edition(client, edition["slug"])
            print(f"  ingested {ingest_translation(conn, edition, texts)} ayahs")

    print("\nnext: python scripts/build_phrases.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
