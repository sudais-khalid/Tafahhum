"""Splitting a Tafsir commentary into retrievable passages.

A commentary on a single ayah can run to tens of thousands of characters —
al-Tabari on 2:255 is over 32,000. That is far too coarse to retrieve: a query
about one clause in the ayah would return the entire discussion, and an embedding
of the whole block would be an average of a dozen unrelated topics.

Chunking is therefore a retrieval decision, and it is made structurally rather
than by character count alone. Classical Tafsir has visible internal structure —
the ``القول في تأويل قوله تعالى`` headers that open a lemma, the ``* *``
separators between transmitted reports, and paragraph breaks. Splitting on those
keeps a chunk to one argument, which is what a citation should point at.

Chunks never cross an ayah boundary, because a passage's ayah alignment is what
makes it citable.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from tafahhum.arabic.normalize import normalize_for_display, normalize_for_matching

#: Target size in characters. Arabic averages fewer characters per word than
#: English, so this is roughly 180-250 words — one sustained argument.
TARGET_CHARS = 1200
MAX_CHARS = 2200
MIN_CHARS = 120

# Structural markers that open a new unit of commentary.
_LEMMA_HEADER = re.compile(
    r"(?:^|\n)\s*(?:القول في تأويل قوله|وقوله تعالى|وقوله|القول في|"
    r"تفسير قوله تعالى|يقول تعالى ذكره)"
)

# Separator lines used between transmitted reports in printed editions.
_SEPARATOR = re.compile(r"\n\s*\*\s*\*\s*\n|\n\s*-{3,}\s*\n|\n\s*={3,}\s*\n")

# Sentence boundaries, for the rare paragraph that alone exceeds MAX_CHARS.
_SENTENCE_END = re.compile(r"(?<=[.؟!])\s+|(?<=۔)\s+")

_PARAGRAPH = re.compile(r"\n\s*\n")


@dataclass(frozen=True)
class Chunk:
    """One passage-to-be."""

    index: int
    raw_text: str
    normalized_text: str
    display_text: str
    char_count: int

    @classmethod
    def of(cls, index: int, text: str) -> Chunk:
        return cls(
            index=index,
            raw_text=text,
            normalized_text=normalize_for_matching(text),
            display_text=normalize_for_display(text),
            char_count=len(text),
        )


def _split_structural(text: str) -> list[str]:
    """Break text at the strongest structural boundaries available."""
    units: list[str] = []
    for section in _SEPARATOR.split(text):
        if not section.strip():
            continue
        # Insert a break before each lemma header so a new lemma starts a unit.
        marked = _LEMMA_HEADER.sub(lambda m: "\n\n" + m.group(0).lstrip("\n"), section)
        for para in _PARAGRAPH.split(marked):
            para = para.strip()
            if para:
                units.append(para)
    return units


def _split_oversized(unit: str) -> list[str]:
    """Split a single over-long paragraph on sentence boundaries."""
    if len(unit) <= MAX_CHARS:
        return [unit]

    pieces: list[str] = []
    current = ""
    for sentence in _SENTENCE_END.split(unit):
        if not sentence.strip():
            continue
        if current and len(current) + len(sentence) + 1 > TARGET_CHARS:
            pieces.append(current.strip())
            current = sentence
        else:
            current = f"{current} {sentence}".strip()
    if current.strip():
        pieces.append(current.strip())

    # A single sentence longer than MAX_CHARS is left intact rather than cut
    # mid-clause: an unreadable fragment is worse than an oversized passage.
    return pieces or [unit]


def chunk_commentary(text: str, *, target: int = TARGET_CHARS) -> list[Chunk]:
    """Split one ayah's commentary into passages.

    Units are accumulated until adding the next would overshoot the target, which
    keeps whole paragraphs together and produces chunks near the target size
    without ever cutting inside a paragraph that fits.
    """
    if not text or not text.strip():
        return []

    units: list[str] = []
    for unit in _split_structural(text):
        units.extend(_split_oversized(unit))

    chunks: list[str] = []
    current = ""
    for unit in units:
        if not current:
            current = unit
        elif len(current) + len(unit) + 2 <= target:
            current = f"{current}\n\n{unit}"
        else:
            chunks.append(current)
            current = unit
    if current:
        chunks.append(current)

    # Fold a trailing scrap into its predecessor rather than emitting a passage
    # too short to carry meaning on its own.
    if len(chunks) > 1 and len(chunks[-1]) < MIN_CHARS:
        chunks[-2] = f"{chunks[-2]}\n\n{chunks[-1]}"
        chunks.pop()

    return [Chunk.of(i, c) for i, c in enumerate(chunks)]
