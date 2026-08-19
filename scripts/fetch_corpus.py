"""Fetch a bounded slice of the Tafsir corpus and ingest it.

This populates enough of the corpus to exercise the whole pipeline end to end.
It is a development seeding tool, not the production ingestion path: the
production path starts from an identified print edition and its scans, so that
citations resolve to a page. See docs/CORPUS_PIPELINE.md.

Usage:
    python scripts/fetch_corpus.py            # fetch + ingest the default slice
    python scripts/fetch_corpus.py --no-fetch # ingest what is already cached
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx
import psycopg

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from tafahhum.core.config import get_settings  # noqa: E402
from tafahhum.core.enums import CopyrightStatus, VerificationStatus  # noqa: E402
from tafahhum.corpus.ingest import (  # noqa: E402
    SourceCommentary,
    SourceWork,
    ingest_commentaries,
)

CACHE = ROOT / "data" / "seed" / "tafsir"
QURAN_CACHE = ROOT / "data" / "quran"

TAFSIR_BASE = "https://raw.githubusercontent.com/spa5k/tafsir_api/main/tafsir"
SOURCE_NAME = "spa5k/tafsir_api (aggregating quran.com)"
LICENSE_NOTE = (
    "Text obtained from an open aggregation of digital Tafsir editions. The "
    "underlying print edition is not identified by the source, so edition-level "
    "licence status is UNKNOWN and must be established before redistribution."
)

# Ayahs to seed. Chosen to cover the reference slice (2:255), a short complete
# surah, and a run of neighbouring ayahs so range queries have something to find.
AYAH_SET: list[tuple[int, int]] = (
    [(1, a) for a in range(1, 8)]
    + [(2, a) for a in range(253, 261)]
    + [(2, 285), (2, 286)]
    + [(112, a) for a in range(1, 5)]
)

# Works to seed, most historically significant first.
WORKS: list[dict[str, str]] = [
    {
        "slug": "tabari-jami-al-bayan",
        "source_slug": "ar-tafsir-al-tabari",
        "title_ar": "جامع البيان عن تأويل آي القرآن",
        "title_en": "Jami al-Bayan an Tawil Ay al-Quran",
        "author_ar": "محمد بن جرير الطبري",
        "author_en": "Muhammad ibn Jarir al-Tabari",
    },
    {
        "slug": "qurtubi-al-jami-li-ahkam",
        "source_slug": "ar-tafseer-al-qurtubi",
        "title_ar": "الجامع لأحكام القرآن",
        "title_en": "Al-Jami li-Ahkam al-Quran",
        "author_ar": "محمد بن أحمد القرطبي",
        "author_en": "Muhammad ibn Ahmad al-Qurtubi",
    },
    {
        "slug": "ibn-kathir-tafsir-al-quran-al-azim",
        "source_slug": "ar-tafsir-ibn-kathir",
        "title_ar": "تفسير القرآن العظيم",
        "title_en": "Tafsir al-Quran al-Azim",
        "author_ar": "إسماعيل بن عمر ابن كثير",
        "author_en": "Ismail ibn Umar Ibn Kathir",
    },
    {
        "slug": "baghawi-maalim-al-tanzil",
        "source_slug": "ar-tafsir-al-baghawi",
        "title_ar": "معالم التنزيل",
        "title_en": "Maalim al-Tanzil",
        "author_ar": "الحسين بن مسعود البغوي",
        "author_en": "al-Husayn ibn Masud al-Baghawi",
    },
    {
        "slug": "zamakhshari-al-kashshaf",
        "source_slug": "al-kashshaf-al-zamakhshari",
        "title_ar": "الكشاف عن حقائق التنزيل",
        "title_en": "Al-Kashshaf an Haqaiq al-Tanzil",
        "author_ar": "محمود بن عمر الزمخشري",
        "author_en": "Mahmud ibn Umar al-Zamakhshari",
    },
    {
        "slug": "razi-mafatih-al-ghayb",
        "source_slug": "tafsir-al-razi",
        "title_ar": "مفاتيح الغيب",
        "title_en": "Mafatih al-Ghayb",
        "author_ar": "فخر الدين الرازي",
        "author_en": "Fakhr al-Din al-Razi",
    },
    {
        "slug": "baydawi-anwar-al-tanzil",
        "source_slug": "tafsir-al-baydawi",
        "title_ar": "أنوار التنزيل وأسرار التأويل",
        "title_en": "Anwar al-Tanzil wa Asrar al-Tawil",
        "author_ar": "عبد الله بن عمر البيضاوي",
        "author_en": "Abdullah ibn Umar al-Baydawi",
    },
    {
        "slug": "ibn-atiyyah-al-muharrar-al-wajiz",
        "source_slug": "al-muharrar-al-wajiz-ibn-atiyyah",
        "title_ar": "المحرر الوجيز",
        "title_en": "Al-Muharrar al-Wajiz",
        "author_ar": "عبد الحق بن غالب ابن عطية",
        "author_en": "Abd al-Haqq ibn Ghalib Ibn Atiyyah",
    },
    {
        "slug": "jalalayn",
        "source_slug": "ar-tafsir-al-jalalayn",
        "title_ar": "تفسير الجلالين",
        "title_en": "Tafsir al-Jalalayn",
        "author_ar": "جلال الدين المحلي وجلال الدين السيوطي",
        "author_en": "Jalal al-Din al-Mahalli and Jalal al-Din al-Suyuti",
    },
    {
        "slug": "saadi-taysir-al-karim",
        "source_slug": "ar-tafsir-as-saadi",
        "title_ar": "تيسير الكريم الرحمن",
        "title_en": "Taysir al-Karim al-Rahman",
        "author_ar": "عبد الرحمن بن ناصر السعدي",
        "author_en": "Abd al-Rahman ibn Nasir al-Sadi",
    },
]


def fetch_tafsir(client: httpx.Client, source_slug: str, surah: int, ayah: int) -> None:
    dest = CACHE / source_slug / str(surah) / f"{ayah}.json"
    if dest.exists():
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    url = f"{TAFSIR_BASE}/{source_slug}/{surah}/{ayah}.json"
    try:
        r = client.get(url, timeout=30)
        if r.status_code == 200:
            dest.write_text(r.text, encoding="utf-8")
        elif r.status_code == 404:
            # Not every work covers every ayah; record the gap rather than
            # retrying it on the next run.
            dest.write_text(
                json.dumps({"surah": surah, "ayah": ayah, "text": ""}),
                encoding="utf-8",
            )
    except httpx.HTTPError as exc:
        print(f"  ! {source_slug} {surah}:{ayah} {exc}", file=sys.stderr)


def fetch_all_tafsir() -> None:
    print(f"fetching {len(WORKS)} works x {len(AYAH_SET)} ayahs ...")
    with httpx.Client(follow_redirects=True) as client:
        with ThreadPoolExecutor(max_workers=8) as pool:
            futures = [
                pool.submit(fetch_tafsir, client, w["source_slug"], s, a)
                for w in WORKS
                for (s, a) in AYAH_SET
            ]
            for f in futures:
                f.result()
    print("  cached")


def fetch_quran() -> dict:
    """Fetch the Quranic text for the seeded ayahs (Uthmani script)."""
    dest = QURAN_CACHE / "ayahs.json"
    if dest.exists():
        return json.loads(dest.read_text(encoding="utf-8"))

    out: dict[str, dict] = {}
    surahs = sorted({s for s, _ in AYAH_SET})
    with httpx.Client(follow_redirects=True) as client:
        for surah in surahs:
            r = client.get(
                f"https://api.alquran.cloud/v1/surah/{surah}/quran-uthmani", timeout=30
            )
            r.raise_for_status()
            for a in r.json()["data"]["ayahs"]:
                out[f"{surah}:{a['numberInSurah']}"] = {
                    "surah": surah,
                    "ayah": a["numberInSurah"],
                    "text": a["text"],
                    "juz": a.get("juz"),
                    "page": a.get("page"),
                    "sajda": bool(a.get("sajda")),
                }
            time.sleep(0.2)
    dest.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    return out


def ingest_quran(conn: psycopg.Connection, ayahs: dict) -> int:
    from tafahhum.arabic.normalize import normalize_for_matching

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO quran_text_source
                (slug, name_ar, name_en, riwayah, script_style, source_url,
                 license, copyright_status, is_default, verification_status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, true, %s)
            ON CONFLICT (slug) DO UPDATE SET name_en = EXCLUDED.name_en
            RETURNING id
            """,
            (
                "hafs-uthmani",
                "حفص عن عاصم - الرسم العثماني",
                "Hafs an Asim, Uthmani script",
                "Hafs an Asim",
                "uthmani",
                "https://api.alquran.cloud/",
                "Tanzil.net Quran text",
                CopyrightStatus.PUBLIC_DOMAIN.value,
                VerificationStatus.UNVERIFIED.value,
            ),
        )
        source_id = cur.fetchone()[0]

        count = 0
        for rec in ayahs.values():
            cur.execute(
                """
                INSERT INTO ayah
                    (text_source_id, surah_number, ayah_number, text_uthmani,
                     text_normalized, juz, page_madani, sajdah)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (text_source_id, surah_number, ayah_number)
                DO UPDATE SET text_uthmani = EXCLUDED.text_uthmani
                """,
                (
                    source_id,
                    rec["surah"],
                    rec["ayah"],
                    rec["text"],
                    normalize_for_matching(rec["text"]),
                    rec.get("juz"),
                    rec.get("page"),
                    rec.get("sajda", False),
                ),
            )
            count += 1
        conn.commit()
    return count


def load_cached(source_slug: str) -> list[SourceCommentary]:
    out = []
    for surah, ayah in AYAH_SET:
        f = CACHE / source_slug / str(surah) / f"{ayah}.json"
        if not f.exists():
            continue
        data = json.loads(f.read_text(encoding="utf-8"))
        out.append(
            SourceCommentary(surah=surah, ayah=ayah, text=data.get("text") or "")
        )
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-fetch", action="store_true", help="use cached files only")
    args = parser.parse_args()

    if not args.no_fetch:
        fetch_all_tafsir()

    settings = get_settings()
    with psycopg.connect(settings.dsn) as conn:
        print("ingesting Quranic text ...")
        ayahs = fetch_quran()
        n = ingest_quran(conn, ayahs)
        print(f"  {n} ayahs")

        print("ingesting Tafsir works ...")
        total = 0
        for w in WORKS:
            commentaries = load_cached(w["source_slug"])
            if not commentaries:
                print(f"  ! no cached data for {w['slug']}")
                continue
            work = SourceWork(
                slug=w["slug"],
                title_ar=w["title_ar"],
                title_en=w["title_en"],
                author_name_ar=w["author_ar"],
                author_name_en=w["author_en"],
                source_url=f"{TAFSIR_BASE}/{w['source_slug']}",
                source_name=SOURCE_NAME,
                license_note=LICENSE_NOTE,
            )
            report = ingest_commentaries(conn, work, commentaries)
            total += report.passages_written
            print(f"  {report}")
        print(f"total passages: {total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
