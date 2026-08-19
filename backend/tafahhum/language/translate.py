"""Translating source passages into a user's language.

This is the second, slower translation path. `pivot.py` carries a *query* into
Arabic for retrieval; this carries a *passage* into the reader's language for
comprehension. They have opposite requirements: a query needs good search terms,
a passage needs faithfulness.

## The rules this path must not break

A translation is a derived artefact. It is:

- stored separately from the passage, in `passage_translation`
- attributed to a translator — a person, or a named model
- labelled as a translation wherever it is shown
- displayed *beside* the Arabic, never instead of it
- never the text of a citation

The last two are the ones that matter. A reader must always be able to see what
the Mufassir actually wrote, and a citation must always point at that, because a
translation is an interpretation and this system exists to keep interpretation
distinguishable from source.

Machine translations are stored as MACHINE_PROPOSED. They never reach VERIFIED
without a named human reviewer, exactly like OCR output.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Protocol

import psycopg

from tafahhum.core.enums import Language, VerificationStatus


@dataclass(frozen=True)
class Translation:
    text: str
    language: Language
    translator_kind: str          # 'HUMAN' | 'MACHINE'
    translator_name: str
    model_name: str | None
    verification_status: VerificationStatus
    note: str | None = None

    @property
    def is_machine(self) -> bool:
        return self.translator_kind == "MACHINE"


class PassageTranslator(Protocol):
    name: str

    def available(self) -> bool: ...

    def translate(self, text: str, *, target: Language, source: Language) -> Translation: ...


_SYSTEM = """You are translating passages of classical Islamic Quranic exegesis \
(Tafsir) for a scholarly research platform. The reader sees your translation \
beside the original, which stays on screen.

Requirements:
- Translate faithfully. Do not summarise, expand, modernise, or smooth over \
difficulty. If the original is elliptical or hard, the translation should be too.
- Keep technical terms as terms. Transliterate and gloss on first use where it \
helps: tafsir, isnad, naskh, ijma, qira'at, asbab al-nuzul, sunnah.
- Keep the names of people and books in recognisable transliteration; do not \
translate a personal name into its literal meaning.
- Quranic text quoted inside the passage must be rendered as a translation of \
the Quran and marked with « » so the reader can see where revelation is being \
quoted rather than commented on.
- Where a chain of narration appears, keep it intact; do not compress it.
- Where the source is ambiguous, translate the ambiguity rather than resolving \
it. Add nothing that is not in the text — no clarifying interpretation, no \
implied subject you cannot see, no bridging sentence.
- If a stretch is unreadable or corrupt, write [unclear] rather than guessing.

Output only the translation. No preamble, no notes, no commentary of your own."""

_LANG_NAME = {
    Language.EN: "English",
    Language.UR: "Urdu",
    Language.AR: "Arabic",
}


class ClaudeTranslator:
    """Model-backed passage translation."""

    name = "claude-translator"

    def __init__(self, model: str = "claude-opus-5", client=None):
        self.model = model
        self._client = client

    def available(self) -> bool:
        try:
            import anthropic  # noqa: F401
        except ImportError:
            return False
        from pathlib import Path

        return bool(
            os.environ.get("ANTHROPIC_API_KEY")
            or os.environ.get("ANTHROPIC_AUTH_TOKEN")
            or Path.home().joinpath(".config", "anthropic").exists()
        )

    @property
    def client(self):
        if self._client is None:
            import anthropic

            self._client = anthropic.Anthropic()
        return self._client

    def translate(
        self, text: str, *, target: Language, source: Language = Language.AR
    ) -> Translation:
        if target is source:
            return Translation(
                text=text, language=target, translator_kind="HUMAN",
                translator_name="(source language)", model_name=None,
                verification_status=VerificationStatus.VERIFIED,
                note="No translation applied; this is the source language.",
            )

        prompt = (
            f"Translate this {_LANG_NAME[source]} passage into "
            f"{_LANG_NAME[target]}.\n\n{text}"
        )
        response = self.client.messages.create(
            model=self.model,
            max_tokens=8000,
            system=[{"type": "text", "text": _SYSTEM, "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": prompt}],
        )

        if response.stop_reason == "refusal":
            return Translation(
                text="", language=target, translator_kind="MACHINE",
                translator_name=self.name, model_name=self.model,
                verification_status=VerificationStatus.UNVERIFIED,
                note="Translation declined by the model.",
            )

        out = "".join(b.text for b in response.content if b.type == "text").strip()
        return Translation(
            text=out,
            language=target,
            translator_kind="MACHINE",
            translator_name=self.name,
            model_name=self.model,
            verification_status=VerificationStatus.MACHINE_PROPOSED,
            note=(
                "Machine translation, not reviewed by a human. The Arabic beside "
                "it is the source; cite that, not this."
            ),
        )


# ---------------------------------------------------------------------------
# Local model
# ---------------------------------------------------------------------------

def looks_degenerate(text: str, *, min_words: int = 12) -> tuple[bool, str | None]:
    """Detect the repetition collapse small models fall into.

    A 7B model asked for a language it was not trained well on will often emit a
    single token forever — "اللہ نے نے نے نے نے …". The output is fluent-looking
    garbage, and storing it would put nonsense under a passage where a reader
    expects a translation. Rejecting it is better than showing it.

    Two checks: one token dominating the output, and a short run repeating.
    """
    words = text.split()
    if len(words) < min_words:
        return False, None

    counts: dict[str, int] = {}
    for w in words:
        counts[w] = counts.get(w, 0) + 1
    top, n = max(counts.items(), key=lambda kv: kv[1])
    if n / len(words) > 0.35:
        return True, f"token {top!r} is {n / len(words):.0%} of the output"

    # The same short phrase repeated back to back.
    for size in (1, 2, 3):
        run = 1
        for i in range(size, len(words), size):
            if words[i : i + size] == words[i - size : i]:
                run += 1
                if run >= 8:
                    return True, f"{size}-word phrase repeats {run}+ times"
            else:
                run = 1
    return False, None


class OllamaTranslator:
    """Translation through a locally running Ollama model.

    Exists so the system is useful without cloud credentials. Quality depends
    entirely on the model: a code-tuned model handles English acceptably and
    collapses on Urdu, so `looks_degenerate` gates every result and a rejected
    output is reported rather than stored.
    """

    name = "ollama"

    def __init__(
        self,
        model: str | None = None,
        host: str = "http://127.0.0.1:11434",
        timeout: float = 300.0,
    ):
        self.model = model or os.environ.get("TAFAHHUM_OLLAMA_MODEL", "")
        self.host = host.rstrip("/")
        self.timeout = timeout

    def _tags(self) -> list[str]:
        import httpx

        try:
            r = httpx.get(f"{self.host}/api/tags", timeout=5.0)
            r.raise_for_status()
            return [m["name"] for m in r.json().get("models", [])]
        except Exception:
            return []

    def available(self) -> bool:
        tags = self._tags()
        if not tags:
            return False
        if self.model:
            return self.model in tags
        # No model configured: adopt whatever is installed, preferring a
        # multilingual family over a code-tuned one.
        preferred = ("aya", "gemma", "llama", "mistral", "qwen")
        for family in preferred:
            for tag in tags:
                if family in tag and "coder" not in tag:
                    self.model = tag
                    return True
        self.model = tags[0]
        return True

    def translate(
        self, text: str, *, target: Language, source: Language = Language.AR
    ) -> Translation:
        import httpx

        if target is source:
            return Translation(
                text=text, language=target, translator_kind="HUMAN",
                translator_name="(source language)", model_name=None,
                verification_status=VerificationStatus.VERIFIED,
            )
        if not self.model:
            self.available()

        # A local model has no system-prompt channel here, so the instructions
        # are prepended to the user prompt instead.
        prompt = (
            f"{_SYSTEM}\n\n"
            f"Translate this {_LANG_NAME[source]} passage into "
            f"{_LANG_NAME[target]}.\n\n{text}"
        )
        try:
            response = httpx.post(
                f"{self.host}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    # Deterministic, and with a repeat penalty that discourages
                    # the collapse the guard below catches.
                    "options": {
                        "temperature": 0,
                        "repeat_penalty": 1.15,
                        "num_predict": 2048,
                    },
                },
                timeout=self.timeout,
            )
            response.raise_for_status()
            out = response.json().get("response", "").strip()
        except Exception as exc:
            return Translation(
                text="", language=target, translator_kind="MACHINE",
                translator_name=self.name, model_name=self.model,
                verification_status=VerificationStatus.UNVERIFIED,
                note=f"Local translation failed: {exc}",
            )

        degenerate, reason = looks_degenerate(out)
        if degenerate:
            return Translation(
                text="", language=target, translator_kind="MACHINE",
                translator_name=self.name, model_name=self.model,
                verification_status=VerificationStatus.UNVERIFIED,
                note=(
                    f"Local model produced degenerate output ({reason}) and it was "
                    f"discarded. {self.model} is not adequate for "
                    f"{_LANG_NAME[target]}; install a multilingual model."
                ),
            )

        return Translation(
            text=out,
            language=target,
            translator_kind="MACHINE",
            translator_name=self.name,
            model_name=self.model,
            verification_status=VerificationStatus.MACHINE_PROPOSED,
            note="Local machine translation. The Arabic beside it is the source.",
        )


def select_translator() -> PassageTranslator:
    """Prefer a hosted model, fall back to a local one, else nothing.

    Ordering is by expected quality on classical Arabic, not by cost: a wrong
    translation of exegesis is worse than an absent one, and an absent one is
    reported honestly.
    """
    hosted = ClaudeTranslator()
    if hosted.available():
        return hosted
    local = OllamaTranslator()
    if local.available():
        return local
    return hosted  # unavailable; callers surface the 503


_translator: PassageTranslator = select_translator()


def set_translator(t: PassageTranslator) -> None:
    """Install a different translator (a local model, or a human workflow)."""
    global _translator
    _translator = t


def get_translator() -> PassageTranslator:
    return _translator


# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------

def fetch_stored(
    conn: psycopg.Connection, passage_id: str, target: Language
) -> Translation | None:
    """Return a stored translation, preferring a human one over a machine one."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT text, translator_kind, translator_name, model_name,
                   verification_status::text AS verification_status
            FROM passage_translation
            WHERE passage_id = %s AND language = %s
            ORDER BY
                CASE translator_kind WHEN 'HUMAN' THEN 0 ELSE 1 END,
                CASE verification_status::text WHEN 'VERIFIED' THEN 0 ELSE 1 END
            LIMIT 1
            """,
            (passage_id, target.value),
        )
        row = cur.fetchone()

    if row is None:
        return None
    return Translation(
        text=row["text"],
        language=target,
        translator_kind=row["translator_kind"],
        translator_name=row["translator_name"],
        model_name=row["model_name"],
        verification_status=VerificationStatus(row["verification_status"]),
    )


def fetch_many(
    conn: psycopg.Connection, passage_ids: list[str], target: Language
) -> dict[str, Translation]:
    """Load cached translations for a whole result set in one round trip.

    A query returns a dozen passages; fetching their translations one at a time
    would make the number of database calls a function of result size for no
    reason. Human translations win over machine ones, and verified over
    unverified, using the same precedence as `fetch_stored`.
    """
    if not passage_ids:
        return {}

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT DISTINCT ON (passage_id)
                   passage_id, text, translator_kind, translator_name, model_name,
                   verification_status::text AS verification_status
            FROM passage_translation
            WHERE passage_id = ANY(%s::uuid[]) AND language = %s
            ORDER BY passage_id,
                     CASE translator_kind WHEN 'HUMAN' THEN 0 ELSE 1 END,
                     CASE verification_status::text WHEN 'VERIFIED' THEN 0 ELSE 1 END
            """,
            (passage_ids, target.value),
        )
        rows = cur.fetchall()

    return {
        str(r["passage_id"]): Translation(
            text=r["text"],
            language=target,
            translator_kind=r["translator_kind"],
            translator_name=r["translator_name"],
            model_name=r["model_name"],
            verification_status=VerificationStatus(r["verification_status"]),
        )
        for r in rows
    }


def store(conn: psycopg.Connection, passage_id: str, translation: Translation) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO passage_translation
                (passage_id, language, text, translator_kind, translator_name,
                 model_name, verification_status)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (passage_id, language, translator_name)
            DO UPDATE SET text = EXCLUDED.text,
                          model_name = EXCLUDED.model_name,
                          verification_status = EXCLUDED.verification_status
            """,
            (
                passage_id,
                translation.language.value,
                translation.text,
                translation.translator_kind,
                translation.translator_name,
                translation.model_name,
                translation.verification_status.value,
            ),
        )
    conn.commit()


def translate_passage(
    conn: psycopg.Connection,
    passage_id: str,
    *,
    target: Language,
    force: bool = False,
) -> tuple[Translation | None, str]:
    """Return a translation for a passage, from cache or freshly produced.

    Returns `(translation, status)` where status is one of `cached`, `fresh`,
    `unavailable`, or `not_found`. Translations are cached because they cost
    money and a passage's text does not change — `raw_text` is immutable, so a
    cached translation cannot silently drift from its source.
    """
    if not force:
        cached = fetch_stored(conn, passage_id, target)
        if cached is not None:
            return cached, "cached"

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT COALESCE(verified_text, raw_text) AS text, language::text AS language
            FROM passage WHERE id = %s
            """,
            (passage_id,),
        )
        row = cur.fetchone()

    if row is None:
        return None, "not_found"

    translator = get_translator()
    if not translator.available():
        return None, "unavailable"

    translation = translator.translate(
        row["text"], target=target, source=Language(row["language"])
    )
    if translation.text:
        store(conn, passage_id, translation)
    return translation, "fresh"
