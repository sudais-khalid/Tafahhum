"""OCR engines.

OCR is a probabilistic extraction step, not a transcription. Its output is stored
as `ocr_raw_text` (immutable), normalised into `ocr_normalized_text` for matching,
and only becomes `ocr_verified_text` when a human approves it against the page
image. Nothing that has not passed that gate may be cited.

## Why there are two engines

Conventional OCR and vision models fail on different things, and the corpus
contains both kinds of page.

**Tesseract** is fast, free, local, and adequate on typeset Naskh Arabic at 300
DPI. It is close to useless on lithographed Urdu Nastaliq: the script is cursive
with heavy ligature overlap and a diagonal baseline, and Tesseract's Urdu model is
trained predominantly on Naskh-style Urdu.

Measured on page 31 of the Nayl al-Sairin scan (~70 DPI Nastaliq), Tesseract
recovered function words but mangled nearly every proper name, and dropped the
section heading entirely. For a tabaqat work — whose entire value is proper names
and dates — that is not a quality problem, it is a total failure of the thing
being extracted.

**A vision model** reads Nastaliq far more reliably because it recognises words
and context rather than segmenting glyphs. It costs money and requires network
access, so it is opt-in.

Neither engine's output is trusted. The difference is that one produces something
worth reviewing.
"""

from __future__ import annotations

import base64
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from tafahhum.arabic.normalize import normalize_for_matching
from tafahhum.core.enums import Language


@dataclass(frozen=True)
class OcrResult:
    """What an engine produced, and how much to trust it."""

    text: str
    engine: str
    engine_version: str
    #: Engine-reported confidence in 0..1, or None when the engine reports none.
    #: Values are NOT comparable across engines and must never be averaged.
    confidence: float | None
    language: Language
    note: str | None = None

    @property
    def normalized(self) -> str:
        return normalize_for_matching(self.text)

    @property
    def is_empty(self) -> bool:
        return not self.text.strip()


class OcrEngine(Protocol):
    name: str

    def available(self) -> bool: ...

    def read_page(self, image_path: Path, *, language: Language) -> OcrResult: ...


# ---------------------------------------------------------------------------
# Tesseract
# ---------------------------------------------------------------------------

_TESS_LANG = {
    Language.AR: "ara",
    Language.UR: "urd+ara",   # Urdu pages carry Arabic quotations
    Language.EN: "eng",
}


class TesseractEngine:
    """Local Tesseract. Baseline quality; poor on Nastaliq."""

    name = "tesseract"

    def __init__(self, binary: str = "tesseract", tessdata: str | None = None):
        self.binary = binary
        self.tessdata = tessdata or os.environ.get("TESSDATA_PREFIX")

    def available(self) -> bool:
        return shutil.which(self.binary) is not None

    def _version(self) -> str:
        try:
            out = subprocess.run(
                [self.binary, "--version"], capture_output=True, text=True, timeout=20
            )
            return out.stdout.splitlines()[0].strip() if out.stdout else "unknown"
        except (OSError, subprocess.SubprocessError):
            return "unknown"

    def read_page(self, image_path: Path, *, language: Language) -> OcrResult:
        lang = _TESS_LANG.get(language, "ara")
        env = dict(os.environ)
        if self.tessdata:
            env["TESSDATA_PREFIX"] = self.tessdata

        with tempfile.TemporaryDirectory() as tmp:
            stem = Path(tmp) / "out"
            # TSV carries per-word confidence, which plain text does not. It is
            # requested with -c rather than the `tsv` config-file argument,
            # because some distributions ship tessdata without a configs/
            # directory and the config-file form then silently produces no TSV.
            subprocess.run(
                [
                    self.binary, str(image_path), str(stem),
                    "-l", lang, "--psm", "6",
                    "-c", "tessedit_create_tsv=1",
                    "-c", "tessedit_create_txt=1",
                ],
                capture_output=True, env=env, timeout=300, check=False,
            )
            tsv = stem.with_suffix(".tsv")
            txt = stem.with_suffix(".txt")
            if tsv.exists():
                text, confidence = _parse_tesseract_tsv(tsv)
            elif txt.exists():
                # Text still beats nothing; the missing confidence is recorded
                # as None rather than filled with a plausible number.
                text, confidence = txt.read_text(encoding="utf-8", errors="replace"), None
            else:
                text, confidence = "", None

        return OcrResult(
            text=text,
            engine=self.name,
            engine_version=self._version(),
            confidence=confidence,
            language=language,
            note=(
                "Tesseract is unreliable on lithographed Nastaliq; treat proper "
                "names in this output as unread rather than as read incorrectly."
                if language is Language.UR
                else None
            ),
        )


def _parse_tesseract_tsv(path: Path) -> tuple[str, float | None]:
    """Rebuild text from Tesseract TSV and average the per-word confidences."""
    lines: dict[tuple[int, int, int], list[str]] = {}
    confidences: list[float] = []

    for row in path.read_text(encoding="utf-8", errors="replace").splitlines()[1:]:
        parts = row.split("\t")
        if len(parts) < 12:
            continue
        word = parts[11].strip()
        if not word:
            continue
        try:
            conf = float(parts[10])
        except ValueError:
            continue
        if conf < 0:
            continue
        confidences.append(conf / 100.0)
        key = (int(parts[2]), int(parts[3]), int(parts[4]))
        lines.setdefault(key, []).append(word)

    text = "\n".join(" ".join(words) for words in lines.values())
    mean = sum(confidences) / len(confidences) if confidences else None
    return text, mean


# ---------------------------------------------------------------------------
# Vision model
# ---------------------------------------------------------------------------

_VISION_SYSTEM = """You are transcribing a scanned page from a printed book for a \
scholarly corpus. Transcribe exactly what is on the page.

Rules:
- Reproduce the text verbatim. Do not translate, modernise, correct, summarise, \
or complete anything.
- Preserve the original script. Urdu stays in Urdu; Arabic quotations stay in Arabic.
- Preserve line and paragraph structure. Keep headings on their own lines.
- Where the scan is too degraded to read a word, write [؟] in its place. Do not \
guess a plausible word — an explicit gap is useful and a wrong name is not.
- Transcribe the printed page number if one is visible, on its own first line, \
as: [page: N]
- Do not transcribe watermarks, library stamps, or website URLs added to the scan.
- Output only the transcription. No commentary, no preamble."""


class VisionOcrEngine:
    """Claude vision transcription. Handles Nastaliq; requires credentials.

    Uses the Batches API when transcribing many pages, which halves the cost and
    suits a job that is not latency-sensitive.
    """

    name = "claude-vision"

    def __init__(self, model: str = "claude-opus-5", client=None):
        self.model = model
        self._client = client

    def available(self) -> bool:
        try:
            import anthropic  # noqa: F401
        except ImportError:
            return False
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

    @staticmethod
    def _image_block(image_path: Path) -> dict:
        media = "image/png" if image_path.suffix.lower() == ".png" else "image/jpeg"
        data = base64.standard_b64encode(image_path.read_bytes()).decode("utf-8")
        return {
            "type": "image",
            "source": {"type": "base64", "media_type": media, "data": data},
        }

    def _user_content(self, image_path: Path, language: Language) -> list[dict]:
        script = "Urdu (Nastaliq) with embedded Arabic quotations" \
            if language is Language.UR else "Arabic (Naskh)"
        return [
            self._image_block(image_path),
            {"type": "text", "text": f"Transcribe this page. The text is {script}."},
        ]

    def read_page(self, image_path: Path, *, language: Language) -> OcrResult:
        response = self.client.messages.create(
            model=self.model,
            max_tokens=16000,
            system=_VISION_SYSTEM,
            messages=[{"role": "user", "content": self._user_content(image_path, language)}],
        )
        if response.stop_reason == "refusal":
            return OcrResult(
                text="", engine=self.name, engine_version=self.model,
                confidence=None, language=language,
                note="Transcription declined by the model.",
            )
        text = "".join(b.text for b in response.content if b.type == "text")
        return OcrResult(
            text=text.strip(),
            engine=self.name,
            engine_version=self.model,
            # The model reports no calibrated confidence. Recording None is
            # honest; inventing a number here would be worse than having none.
            confidence=None,
            language=language,
            note="Machine transcription. Requires human review before citation.",
        )

    def build_batch_requests(
        self, pages: list[tuple[str, Path]], *, language: Language
    ) -> list:
        """Build Batches API requests for many pages.

        Batch processing runs at 50% cost and completes within 24 hours, which
        fits a one-off corpus ingestion far better than 570 synchronous calls.
        """
        from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
        from anthropic.types.messages.batch_create_params import Request

        return [
            Request(
                custom_id=custom_id,
                params=MessageCreateParamsNonStreaming(
                    model=self.model,
                    max_tokens=16000,
                    system=_VISION_SYSTEM,
                    messages=[
                        {"role": "user", "content": self._user_content(path, language)}
                    ],
                ),
            )
            for custom_id, path in pages
        ]


# ---------------------------------------------------------------------------
# Selection
# ---------------------------------------------------------------------------

def select_engine(preferred: str | None = None) -> OcrEngine:
    """Pick an engine, preferring the one that can actually read the page.

    Falls back to Tesseract with a warning rather than failing, so the pipeline
    can be exercised without credentials — but a Nastaliq corpus processed this
    way is a demonstration, not a usable extraction.
    """
    vision = VisionOcrEngine()
    tesseract = TesseractEngine()

    if preferred == "tesseract":
        return tesseract
    if preferred == "vision":
        return vision
    if vision.available():
        return vision
    return tesseract
