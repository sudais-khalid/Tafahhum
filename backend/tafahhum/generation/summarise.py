"""Controlled generation of a conclusion for an ayah.

This is the only place in Tafahhum where text is written rather than quoted, and
a summary of exegesis is itself exegesis. So the module is built around one
question: how do we know the generated text came from the sources?

## Generate in Arabic, verify in Arabic, translate afterwards

The obvious design — generate the summary directly in the reader's language —
makes verification impossible. The passages are Arabic; an English sentence
shares no vocabulary with the Arabic it supposedly summarises, so there is
nothing to check it against and "verification" degrades to trusting that the
citation marker was placed honestly.

Generating in Arabic first means every sentence can be checked against the
passage it cites by actual word overlap. Only the sentences that survive are
translated. That follows the same Arabic-pivot rule as the rest of the system,
and it is the difference between a citation and a claim of a citation.

## What verification catches, and what it does not

Overlap catches a sentence that cites a passage it has nothing to do with — the
common failure where a model produces fluent, plausible commentary and attaches
a citation to it afterwards. It does not catch a subtle misreading of a passage
the sentence genuinely draws on. Nothing here should be read as a claim that the
summary is *correct*; the claim is narrower, that each sentence is traceable to
a specific passage a reader can open and judge.

Everything produced is TAFAHHUM_SYNTHESIS, is never citable as a source, and
reaches VERIFIED only through a human.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from tafahhum.arabic.normalize import normalize_for_matching
from tafahhum.core.enums import Language, VerificationStatus

GENERATOR_VERSION = "tafahhum-summary-v1"

#: Minimum passages before a summary is attempted. Below this there is no
#: synthesis to make, only a restatement of one commentator.
MIN_PASSAGES = 3

#: Fraction of a sentence's content words that must appear in the passage it
#: cites, after clitics are stripped.
#:
#: A summary paraphrases, so this is deliberately far from 1.0. The separation it
#: relies on is wide: a sentence with no relationship to its citation shares no
#: substantive vocabulary at all and scores 0, while a faithful paraphrase reuses
#: some of the passage's key terms. Anything in between those is arbitrary, and
#: one in five is the point chosen.
#:
#: Tuned against a handful of hand-built cases, not an evaluation set. It should
#: be revisited once there are labelled summaries to measure against — see
#: docs/EVALUATION.md.
MIN_SUPPORT = 0.20

#: Above this, a sentence is not a summary of the passage but a copy of it.
#: Reproducing the source and labelling it a synthesis is its own failure mode.
MAX_SUPPORT = 0.92

#: Arabic function words, excluded when measuring overlap: they appear in every
#: sentence and would make unrelated text look supported.
_FUNCTION_WORDS = frozenset(
    [
        "ما", "في", "من", "علي", "الي", "عن", "هو", "هي",
        "هم", "لا", "الا", "ان", "انه", "اني", "الذي", "التي",
        "وهو", "وهي", "له", "لها", "لهم", "به", "بها", "عليه",
        "عليها", "ذلك", "هذا", "هذه", "ثم", "قد", "كان", "كانت",
        "يكون", "قال", "وقد", "وقال", "ايضا", "بين", "عند", "كل",
        "علي", "اذا", "حتي", "لكن", "او", "ام", "بل",
    ]
)

_SYSTEM = """You summarise what a given set of Quranic commentators said about one verse. You \
are not a commentator and you do not issue rulings.

You are given numbered passages. They are your only source.

OUTPUT FORMAT — follow exactly:
Write 4 to 8 lines. One sentence per line. End every line with the number of the passage it \
came from, in square brackets.

Example of the required shape:
<one sentence in Arabic> [1]
<one sentence in Arabic> [2]
<one sentence in Arabic> [1][3]

Rules:
- Write in Arabic.
- A line with no [number] is discarded, so never omit it.
- Do not copy a passage word for word. State in your own words what it says.
- Use only what the numbered passages say. Add no background, history, or outside knowledge, \
however familiar.
- Where passages disagree, give each position on its own line and attribute it. Do not choose \
between them and do not call a disputed reading settled.
- No legal rulings, and no telling the reader what to believe or do.

Output only those lines. No heading, no preamble, no closing remark."""


@dataclass
class SummarySentence:
    text: str
    citations: list[int]
    support: float
    kept: bool
    reason: str | None = None


@dataclass
class SummaryResult:
    summary_ar: str
    raw_output: str
    sentences: list[SummarySentence] = field(default_factory=list)
    cited_passage_ids: list[str] = field(default_factory=list)
    model_name: str = ""
    note: str | None = None

    @property
    def generated(self) -> int:
        return len(self.sentences)

    @property
    def kept(self) -> int:
        return sum(1 for s in self.sentences if s.kept)

    @property
    def removed(self) -> int:
        return self.generated - self.kept

    @property
    def mean_support(self) -> float:
        supported = [s.support for s in self.sentences if s.kept]
        return round(sum(supported) / len(supported), 3) if supported else 0.0

    @property
    def is_usable(self) -> bool:
        return bool(self.summary_ar.strip()) and self.kept > 0


# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------

def build_prompt(ayah_text: str, reference: str, passages: list[dict]) -> str:
    """Assemble the sealed prompt.

    The model sees the ayah and the numbered passages and nothing else — no
    work titles, no author names, no dates. Withholding them keeps the model
    from reaching for what it already knows about al-Tabari and writing that
    instead of what the passage in front of it actually says.
    """
    lines = [f"Verse {reference}:", ayah_text.strip(), "", "Passages:"]
    for i, p in enumerate(passages, start=1):
        body = re.sub(r"\s+", " ", p["text"]).strip()
        lines.append(f"[{i}] {body}")
        lines.append("")
    lines.append(
        "Write the synthesis in Arabic, citing these passages by number."
    )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------

_CITATION = re.compile(r"\[(\d{1,2})\]")
_SENTENCE_SPLIT = re.compile(r"\n+|(?<=[.؟!۔])\s+")


#: Clitics Arabic attaches to the front of a word: conjunctions, prepositions,
#: and the definite article. They are orthographic, not lexical.
_PREFIXES = ("وال", "فال", "بال", "كال", "لل", "ال", "و", "ف", "ب", "ك", "ل")


def _strip_clitics(word: str) -> str:
    """Reduce a word to its stem for overlap purposes.

    Arabic writes conjunctions, prepositions, and the article joined to the
    following word, so والقيوم and القيوم are the same lexical item spelled
    differently. Comparing surface forms made a faithful summary sentence score
    12% against a passage it genuinely drew on — the threshold was measuring
    morphology rather than fidelity. Stripping the clitic makes the score mean
    what it is supposed to mean.
    """
    for prefix in _PREFIXES:
        if word.startswith(prefix) and len(word) - len(prefix) >= 3:
            return word[len(prefix):]
    return word


def content_words(text: str) -> set[str]:
    words = normalize_for_matching(text).split()
    stems = {_strip_clitics(w) for w in words if len(w) >= 4 and w not in _FUNCTION_WORDS}
    return {w for w in stems if len(w) >= 3}


def support_score(sentence: str, passage_text: str) -> float:
    """Fraction of the sentence's content words present in the cited passage.

    Containment rather than Jaccard: a summary sentence is much shorter than the
    passage it draws on, so a symmetric measure would score everything near zero
    regardless of whether the sentence was faithful.
    """
    sentence_words = content_words(sentence)
    if not sentence_words:
        return 0.0
    passage_words = content_words(passage_text)
    return len(sentence_words & passage_words) / len(sentence_words)


#: Latin letters inside Arabic output. Small models occasionally emit a stray
#: token from another script mid-sentence; the text is corrupt, not merely
#: awkward, and must not be shown as though a commentator's view were rendered.
_LATIN_IN_ARABIC = re.compile(r"[A-Za-z]{2,}")


def echoes_the_verse(sentence: str, ayah_text: str) -> float:
    """How much of a sentence is simply the verse restated.

    Observed failure: asked to summarise commentary, a small model recites the
    ayah instead. It scores well against the passages, because the passages
    quote the ayah too — so overlap alone cannot catch it. A summary of what
    commentators said should add something the verse does not already say.
    """
    words = content_words(sentence)
    if not words:
        return 0.0
    return len(words & content_words(ayah_text)) / len(words)


#: Above this share of verse words, a sentence is a recitation, not a summary.
MAX_VERSE_ECHO = 0.6


def verify(
    raw_output: str, passages: list[dict], ayah_text: str = ""
) -> list[SummarySentence]:
    """Check every sentence against the passage it cites."""
    # Collapse spaces and tabs but keep line breaks: the output contract is one
    # sentence per line, so newlines are the primary boundary and flattening
    # them first would leave nothing for the split to find.
    cleaned = re.sub(r"[^\S\n]+", " ", raw_output).strip()
    out: list[SummarySentence] = []

    for raw in _SENTENCE_SPLIT.split(cleaned):
        sentence = raw.strip()
        if len(sentence) < 15:
            continue

        cited = [int(n) for n in _CITATION.findall(sentence)]
        valid = [n for n in cited if 1 <= n <= len(passages)]
        bare = _CITATION.sub("", sentence).strip()

        if _LATIN_IN_ARABIC.search(bare):
            out.append(
                SummarySentence(
                    bare, [], 0.0, False,
                    "output corrupted: Latin characters inside Arabic text",
                )
            )
            continue

        if ayah_text and echoes_the_verse(bare, ayah_text) > MAX_VERSE_ECHO:
            out.append(
                SummarySentence(
                    bare, [], 0.0, False,
                    "restates the verse rather than summarising commentary on it",
                )
            )
            continue

        if not cited:
            out.append(SummarySentence(bare, [], 0.0, False, "no citation"))
            continue
        if not valid:
            out.append(
                SummarySentence(bare, cited, 0.0, False, "citation out of range")
            )
            continue

        # Best-supporting cited passage decides: a sentence drawing on several
        # passages should not be penalised for the weakest of them.
        best = max(support_score(bare, passages[n - 1]["text"]) for n in valid)
        if best > MAX_SUPPORT and len(content_words(bare)) > 6:
            out.append(
                SummarySentence(
                    bare, valid, round(best, 3), False,
                    f"reproduces the passage rather than summarising it ({best:.0%})",
                )
            )
            continue
        if best < MIN_SUPPORT:
            out.append(
                SummarySentence(
                    bare, valid, round(best, 3), False,
                    f"insufficient overlap with cited passage ({best:.0%})",
                )
            )
            continue

        out.append(SummarySentence(bare, valid, round(best, 3), True))

    return out


def assemble(sentences: list[SummarySentence]) -> str:
    """Rebuild the summary from the sentences that survived, keeping markers."""
    parts = []
    for s in sentences:
        if not s.kept:
            continue
        marker = "".join(f"[{n}]" for n in s.citations)
        parts.append(f"{s.text} {marker}")
    return " ".join(parts).strip()


# ---------------------------------------------------------------------------
# Generation
# ---------------------------------------------------------------------------

def summarise(
    ayah_text: str,
    reference: str,
    passages: list[dict],
    *,
    translator=None,
) -> SummaryResult | None:
    """Produce a verified Arabic synthesis, or None when it cannot be grounded.

    `passages` is a list of dicts with `id` and `text`, already narrowed to the
    reader's selected sources. `translator` is any object exposing the
    PassageTranslator protocol; it supplies the model and is what makes the
    backend swappable.
    """
    if len(passages) < MIN_PASSAGES:
        return SummaryResult(
            summary_ar="",
            raw_output="",
            note=(
                f"Only {len(passages)} passage(s) available for this verse in the "
                f"selected sources — too few to synthesise. The passages "
                f"themselves are shown above."
            ),
        )

    if translator is None:
        from tafahhum.language.translate import get_translator

        translator = get_translator()

    if not translator.available():
        return None

    prompt = build_prompt(ayah_text, reference, passages)
    raw = _generate(translator, prompt)
    if not raw:
        return SummaryResult(
            summary_ar="", raw_output="",
            note="The model returned nothing for this verse.",
        )

    sentences = verify(raw, passages, ayah_text)
    summary = assemble(sentences)

    used = sorted({n for s in sentences if s.kept for n in s.citations})
    return SummaryResult(
        summary_ar=summary,
        raw_output=raw,
        sentences=sentences,
        cited_passage_ids=[passages[n - 1]["id"] for n in used],
        model_name=getattr(translator, "model", translator.name),
        note=None if summary else "No sentence could be traced to a cited passage.",
    )


def _generate(translator, prompt: str) -> str:
    """Run the prompt through whichever backend is installed.

    Both backends expose a chat-style call under different names, so this bridges
    them rather than forcing the translator protocol to grow a second method.
    """
    import httpx

    # Local model.
    if getattr(translator, "name", "") == "ollama":
        try:
            response = httpx.post(
                f"{translator.host}/api/generate",
                json={
                    "model": translator.model,
                    "system": _SYSTEM,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.2, "repeat_penalty": 1.1,
                                "num_predict": 1024},
                },
                timeout=translator.timeout,
            )
            response.raise_for_status()
            return response.json().get("response", "").strip()
        except Exception:
            return ""

    # Hosted model.
    try:
        message = translator.client.messages.create(
            model=translator.model,
            max_tokens=2000,
            system=[{"type": "text", "text": _SYSTEM,
                     "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": prompt}],
        )
        if message.stop_reason == "refusal":
            return ""
        return "".join(b.text for b in message.content if b.type == "text").strip()
    except Exception:
        return ""


def status_for(result: SummaryResult) -> VerificationStatus:
    """Machine output is always proposed, never verified."""
    return VerificationStatus.MACHINE_PROPOSED


def translate_summary(summary_ar: str, target: Language, translator=None) -> str | None:
    """Render the verified Arabic summary into the reader's language.

    Translation happens after verification, never before: the citation markers
    are preserved so a reader can still follow each sentence back to its passage.
    """
    if target is Language.AR or not summary_ar.strip():
        return summary_ar

    if translator is None:
        from tafahhum.language.translate import get_translator

        translator = get_translator()
    if not translator.available():
        return None

    result = translator.translate(summary_ar, target=target, source=Language.AR)
    return result.text or None
