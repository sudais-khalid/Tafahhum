"""Neural machine translation for passages.

The previous backend asked a general-purpose 3B chat model to translate. That was
the wrong tool, and it failed in ways specific to being the wrong tool: it
ignored instructions, collapsed into token repetition on Urdu, spliced Latin
characters into Arabic, and took 45 to 80 seconds a passage.

This uses NLLB-200, a model trained for one job. Translation quality aside, the
whole class of instruction-following failures disappears, because there are no
instructions: a sequence goes in, a translated sequence comes out. There is no
prompt to ignore and nothing for the model to be talked out of.

## Why CTranslate2 rather than transformers

The same weights under transformers need roughly 2.4GB of RAM in float32 and
pull in PyTorch. Quantised to int8 under CTranslate2 the model is about 600MB
and several times faster on CPU, and the inference path has no torch dependency
at all. On a machine with under 2GB free that is the difference between working
and swapping.

## Sentences, not passages

NMT models are trained on sentence pairs and degrade on long inputs, quietly
dropping clauses rather than erroring. A commentary passage runs to well over a
thousand characters, so it is split on sentence boundaries, translated piece by
piece, and rejoined. Splitting is also what keeps a single hard sentence from
spoiling the whole passage.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

from tafahhum.core.enums import Language, VerificationStatus

#: NLLB uses FLORES-200 codes rather than ISO-639.
NLLB_CODES = {
    Language.AR: "arb_Arab",
    Language.EN: "eng_Latn",
    Language.UR: "urd_Arab",
    Language.FA: "pes_Arab",
    Language.TR: "tur_Latn",
}

DEFAULT_MODEL_DIR = Path(
    os.environ.get("TAFAHHUM_NLLB_DIR", r"E:\Tafahhum\models\nllb-600m-int8")
)

#: NLLB's positional limit is 512 tokens; well under it keeps quality stable.
MAX_SENTENCE_CHARS = 400

#: How many sentences go through the model at once. Also the failure blast
#: radius: a chunk that raises is retried sentence by sentence.
CHUNK_PIECES = 16

#: Beam width. Four was the default and roughly doubles decode time over two
#: for a difference that does not survive contact with classical Arabic, where
#: the register is the limiting factor rather than the search. Two is the
#: better trade on CPU; raise it with TAFAHHUM_NLLB_BEAM if a passage matters
#: more than the wait.
BEAM_SIZE = max(1, int(os.environ.get("TAFAHHUM_NLLB_BEAM", "2")))

_SENTENCE_END = re.compile(r"(?<=[.؟!۔:])\s+")


@dataclass(frozen=True)
class _Loaded:
    translator: object
    tokenizer: object


class NllbTranslator:
    """Purpose-built translation, loaded once and reused."""

    name = "nllb-200-distilled-600M"

    def __init__(self, model_dir: Path | None = None, compute_type: str = "int8"):
        self.model_dir = Path(model_dir or DEFAULT_MODEL_DIR)
        self.compute_type = compute_type
        self.model = self.name
        self._loaded: _Loaded | None = None

    # -- lifecycle ---------------------------------------------------------

    def available(self) -> bool:
        if not self.model_dir.exists():
            return False
        if not (self.model_dir / "model.bin").exists():
            return False
        try:
            import ctranslate2  # noqa: F401
            import sentencepiece  # noqa: F401
        except ImportError:
            return False
        return True

    def _load(self) -> _Loaded:
        """Load on first use and keep it.

        Loading costs seconds and hundreds of megabytes, so it must not happen
        per request; holding it also means the second translation on a page is
        fast rather than paying the same cost again.
        """
        if self._loaded is not None:
            return self._loaded

        import ctranslate2
        import sentencepiece as spm

        translator = ctranslate2.Translator(
            str(self.model_dir), device="cpu", compute_type=self.compute_type
        )
        sp = spm.SentencePieceProcessor()
        sp.load(str(self.model_dir / "sentencepiece.bpe.model"))

        self._loaded = _Loaded(translator=translator, tokenizer=sp)
        return self._loaded

    # -- translation -------------------------------------------------------

    @staticmethod
    def _split(text: str) -> list[str]:
        """Sentence-sized pieces, none longer than the model handles well."""
        pieces: list[str] = []
        for sentence in _SENTENCE_END.split(re.sub(r"\s+", " ", text).strip()):
            sentence = sentence.strip()
            if not sentence:
                continue
            if len(sentence) <= MAX_SENTENCE_CHARS:
                pieces.append(sentence)
                continue
            # A sentence longer than the limit is broken on commas rather than
            # mid-word, so each piece is still a coherent span.
            current = ""
            for clause in re.split(r"(?<=[,،؛])\s+", sentence):
                if current and len(current) + len(clause) + 1 > MAX_SENTENCE_CHARS:
                    pieces.append(current.strip())
                    current = clause
                else:
                    current = f"{current} {clause}".strip()
            if current.strip():
                pieces.append(current.strip())
        return pieces

    def translate(self, text: str, *, target: Language, source: Language = Language.AR):
        from tafahhum.language.translate import Translation

        if target is source:
            return Translation(
                text=text, language=target, translator_kind="HUMAN",
                translator_name="(source language)", model_name=None,
                verification_status=VerificationStatus.VERIFIED,
            )

        src = NLLB_CODES.get(source)
        tgt = NLLB_CODES.get(target)
        if not src or not tgt:
            return Translation(
                text="", language=target, translator_kind="MACHINE",
                translator_name=self.name, model_name=self.name,
                verification_status=VerificationStatus.UNVERIFIED,
                note=f"NLLB has no code for {source.value} to {target.value}.",
            )

        try:
            loaded = self._load()
        except Exception as exc:
            return Translation(
                text="", language=target, translator_kind="MACHINE",
                translator_name=self.name, model_name=self.name,
                verification_status=VerificationStatus.UNVERIFIED,
                note=f"Could not load the translation model: {exc}",
            )

        pieces = self._split(text)
        if not pieces:
            return Translation(
                text="", language=target, translator_kind="MACHINE",
                translator_name=self.name, model_name=self.name,
                verification_status=VerificationStatus.UNVERIFIED,
                note="Nothing to translate.",
            )

        rendered, failed = self._translate_pieces(loaded, pieces, src, tgt)

        if not rendered:
            return Translation(
                text="", language=target, translator_kind="MACHINE",
                translator_name=self.name, model_name=self.name,
                verification_status=VerificationStatus.UNVERIFIED,
                note="No part of this passage could be translated.",
            )

        note = (
            "Machine translation by a dedicated translation model. The "
            "Arabic beside it is the source; cite that, not this."
        )
        if failed:
            # Saying which part is missing beats presenting a shortened
            # translation as though it were the whole passage.
            note += (
                f" {failed} of {len(pieces)} sentences could not be translated "
                f"and are omitted here; they are present in the Arabic."
            )

        return Translation(
            text=rendered,
            language=target,
            translator_kind="MACHINE",
            translator_name=self.name,
            model_name=f"{self.name} ({self.compute_type})",
            verification_status=VerificationStatus.MACHINE_PROPOSED,
            note=note,
        )

    # -- decoding ----------------------------------------------------------

    def _translate_pieces(
        self, loaded: _Loaded, pieces: list[str], src: str, tgt: str
    ) -> tuple[str, int]:
        """Translate the pieces, losing at most one sentence to any one failure.

        The passage is split into sentences precisely so that one hard sentence
        cannot spoil the rest, but a single `translate_batch` call over every
        piece threw that away: one bad sequence raised, and the whole passage
        came back empty. That is what made translation look unreliable on some
        passages and fine on others.

        So the pieces go through in chunks, and a chunk that raises is retried
        one sentence at a time to isolate the offender. Whatever translates is
        kept, and the caller is told how much was not.
        """
        out: list[str] = []
        failed = 0

        for start in range(0, len(pieces), CHUNK_PIECES):
            chunk = pieces[start : start + CHUNK_PIECES]
            try:
                out.extend(self._decode(loaded, chunk, src, tgt))
                continue
            except Exception:
                pass

            # The chunk failed as a unit. Retry each sentence alone so the
            # damage is bounded to the sentence that actually caused it.
            for piece in chunk:
                try:
                    out.extend(self._decode(loaded, [piece], src, tgt))
                except Exception:
                    failed += 1

        rendered = " ".join(s for s in (t.strip() for t in out) if s)
        return rendered, failed

    def _decode(
        self, loaded: _Loaded, pieces: list[str], src: str, tgt: str
    ) -> list[str]:
        """One batch through the model, returned as plain strings."""
        sp = loaded.tokenizer
        # The source language tag prefixes the sequence; the target tag is what
        # the decoder is forced to start with.
        batch = [[src, *sp.encode(p, out_type=str), "</s>"] for p in pieces]

        results = loaded.translator.translate_batch(
            batch,
            target_prefix=[[tgt]] * len(batch),
            beam_size=BEAM_SIZE,
            max_batch_size=CHUNK_PIECES,
            # Long enough for a full sentence, bounded so a degenerate
            # decode cannot run away.
            max_decoding_length=256,
            repetition_penalty=1.1,
            # A repetition penalty discourages loops; this forbids them
            # outright, which is what actually stopped the Urdu decoder
            # emitting the same clause until it hit the length cap.
            no_repeat_ngram_size=4,
        )

        out: list[str] = []
        for r in results:
            tokens = list(r.hypotheses[0])
            if tokens and tokens[0] == tgt:
                tokens = tokens[1:]
            out.append(sp.decode(tokens))
        return out
