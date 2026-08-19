"""Fetch attributed Quran translations for the seeded ayahs.

The Quranic text in a result is revealed text, and a reader working in English or
Urdu needs it rendered in their language. That rendering must be an established,
attributed translation by a named translator — not machine output. A machine
translation of the Quran presented beside the Arabic would put an unreviewed
paraphrase where a reader expects a recognised one.

    python scripts/fetch_quran_translations.py
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

from tafahhum.core.config import get_settings  # noqa: E402
from tafahhum.core.enums import CopyrightStatus  # noqa: E402

CACHE = ROOT / "data" / "quran"
BASE = "https://api.alquran.cloud/v1/surah"

# Two widely used translations per language. Both are shown as options rather
# than one being declared correct: translation choice is a scholarly preference,
# and the interface names the translator on every rendering.
EDITIONS = [
    {"slug": "en.sahih", "lang": "en", "translator": "Saheeh International"},
    {"slug": "en.yusufali", "lang": "en", "translator": "Abdullah Yusuf Ali"},
    {"slug": "ur.jalandhry", "lang": "ur", "translator": "Fateh Muhammad Jalandhry"},
    {"slug": "ur.junagarhi", "lang": "ur", "translator": "Muhammad Junagarhi"},
]

# Surahs seeded by fetch_corpus.py.
SURAHS = [1, 2, 112]


def fetch(edition: dict) -> dict[str, str]:
    dest = CACHE / f"tr_{edition['slug']}.json"
    if dest.exists():
        return json.loads(dest.read_text(encoding="utf-8"))

    out: dict[str, str] = {}
    with httpx.Client(follow_redirects=True) as client:
        for surah in SURAHS:
            r = client.get(f"{BASE}/{surah}/{edition['slug']}", timeout=40)
            r.raise_for_status()
            for a in r.json()["data"]["ayahs"]:
                out[f"{surah}:{a['numberInSurah']}"] = a["text"]
            time.sleep(0.2)
    dest.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    return out


def main() -> int:
    settings = get_settings()
    total = 0

    with psycopg.connect(settings.dsn) as conn:
        for edition in EDITIONS:
            texts = fetch(edition)
            with conn.cursor() as cur:
                for ref, text in texts.items():
                    surah, ayah = (int(x) for x in ref.split(":"))
                    cur.execute(
                        """
                        INSERT INTO ayah_translation
                            (surah_number, ayah_number, language, translator_name,
                             translation_slug, text, source_url, copyright_status)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (translation_slug, surah_number, ayah_number)
                        DO UPDATE SET text = EXCLUDED.text
                        """,
                        (
                            surah, ayah, edition["lang"], edition["translator"],
                            edition["slug"], text,
                            f"https://api.alquran.cloud/v1/surah/{{surah}}/{edition['slug']}",
                            CopyrightStatus.UNKNOWN.value,
                        ),
                    )
                    total += 1
            conn.commit()
            print(f"  {edition['slug']:16} {edition['translator']:32} {len(texts)} ayahs")

    print(f"stored {total} ayah translations")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
