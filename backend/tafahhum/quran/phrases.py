"""Segmenting an ayah into the phrases its commentators actually treat.

Classical Tafsir is organised phrase by phrase. A commentator writes
``القول في تأويل قوله تعالى`` or ``قوله عز وجل``, quotes a clause of the ayah,
and comments on that clause before moving to the next. Reading tafsir *is*
reading an ayah one clause at a time and hearing what was said about each.

The current interface groups passages by book, which only helps a reader who
already knows the books. Grouping by clause helps a reader who knows the ayah —
which is everyone who arrived with a question about it.

## Where the segmentation comes from

Not from a grammar model, and not from punctuation. From the corpus itself:
commentators mark the clause they are treating with ornate brackets ``﴿ ﴾``, and
those marks are evidence of how the tradition divides the ayah. Collecting every
bracketed quotation across every commentary on an ayah, mapping each back to a
span of the ayah's own words, and merging the overlaps yields the clause
boundaries the commentators use.

That is an extraction, not an inference. A segmentation nobody quoted does not
appear.

## Passages that do not bracket

Roughly half of them, and it varies sharply by edition — al-Tha'alibi's uses no
brackets at all. Those are aligned by word overlap instead: the longest run of
consecutive ayah words appearing in the passage. Weaker evidence, and recorded
as such, so the interface can distinguish a passage that announced its subject
from one whose subject was inferred.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from tafahhum.arabic.normalize import normalize_for_matching

#: Ornate Quranic quotation brackets, and the plain forms some editions use.
_QUOTED = re.compile(r"﴿([^﴾]{2,200})﴾|\{([^{}]{4,200})\}")

#: Headers that announce a new clause under discussion.
LEMMA_HEADERS = (
    "القول في تأويل قوله تعالى",
    "القول في تأويل قوله",
    "قوله عز وجل",
    "قوله تعالى",
    "وقوله تعالى",
    "وقوله عز وجل",
)

#: Minimum words for a quotation to count as a clause marker. Single words are
#: usually a gloss target rather than a structural division.
MIN_PHRASE_WORDS = 2

#: How many separate passages must quote a span before it counts as a division
#: of the ayah. One commentary quoting something is a gloss; several returning
#: to the same clause is how the tradition divides the verse.
MIN_PHRASE_SUPPORT = 3

_HEADER_RE = re.compile("|".join(re.escape(h) for h in LEMMA_HEADERS))


@dataclass(frozen=True)
class Phrase:
    """One clause of an ayah, as the commentators divide it."""

    index: int
    start_word: int          # inclusive, 0-based into the ayah's words
    end_word: int            # inclusive
    text: str                # the ayah's own words for this span
    normalized: str
    #: How many distinct passages quoted this span. Higher means the tradition
    #: treats it as a unit more consistently.
    support: int = 0

    @property
    def word_count(self) -> int:
        return self.end_word - self.start_word + 1


@dataclass
class Alignment:
    """Which phrase a passage comments on, and how that was established."""

    passage_id: str
    phrase_index: int
    #: 'quoted'  — the passage bracketed this clause (strong)
    #: 'overlap' — matched by word overlap (weaker)
    basis: str
    matched_words: int
    confidence: float
    #: True when the passage begins its treatment of this clause here, rather
    #: than continuing one already underway.
    opens_discussion: bool = False


def ayah_words(text: str) -> list[str]:
    """The ayah's words in normalised form, positionally indexed."""
    return normalize_for_matching(text).split()


def extract_quotations(passage_text: str) -> list[str]:
    """Every bracketed Quranic quotation in a passage, normalised."""
    out: list[str] = []
    for match in _QUOTED.finditer(passage_text):
        raw = match.group(1) or match.group(2) or ""
        norm = normalize_for_matching(raw)
        if len(norm.split()) >= 1:
            out.append(norm)
    return out


def _find_span(needle: list[str], haystack: list[str]) -> tuple[int, int] | None:
    """Locate a run of words inside the ayah, allowing a leading/trailing miss.

    Editions differ in whether a quotation includes the conjunction that joins it
    to the previous clause, so an exact match is too brittle. The longest
    contiguous run is used instead.
    """
    if not needle:
        return None

    best: tuple[int, int] | None = None
    best_len = 0

    for start in range(len(haystack)):
        if haystack[start] != needle[0] and needle[0] not in haystack[start]:
            continue
        length = 0
        while (
            start + length < len(haystack)
            and length < len(needle)
            and haystack[start + length] == needle[length]
        ):
            length += 1
        if length > best_len:
            best_len = length
            best = (start, start + length - 1)

    if best is None or best_len < 1:
        return None
    return best


#: Function words occurring in almost any Arabic sentence. A run made only of
#: these is not evidence that a passage is treating the clause containing them.
_FUNCTION_WORDS = frozenset(
    [
        "ما", "في", "من", "علي", "الي", "عن", "هو", "هي",
        "هم", "لا", "الا", "ان", "انه", "اني", "الذي", "التي",
        "له", "لها", "لهم", "به", "بها", "عليه", "عليها", "ذلك",
        "هذا", "هذه", "ثم", "قد", "كان", "كانت", "يكون",
    ]
)


def _is_content_word(word: str) -> bool:
    return len(word) >= 4 and word not in _FUNCTION_WORDS


def _longest_common_run(passage_words: list[str], ayah: list[str]) -> tuple[int, int, int]:
    """Longest run of consecutive ayah words appearing in a passage.

    Runs are scored by the *content* words they contain, not their raw length.
    Scoring by length lets a run of function words win: "له ما في" is three words
    appearing in nearly any Arabic prose, so a passage discussing الحي would
    otherwise be filed under the clause beginning "له ما في السماوات". A run with
    no content word is not evidence of anything and is rejected outright.

    Returns (start, end, length) into the ayah, or (-1, -1, 0).
    """
    passage_set = set(passage_words)
    best_start = best_end = -1
    best_score = 0
    best_len = 0

    run_start = -1
    run_len = 0
    run_content = 0
    for i, word in enumerate(ayah):
        if word in passage_set and len(word) > 1:
            if run_start < 0:
                run_start = i
                run_content = 0
            run_len += 1
            if _is_content_word(word):
                run_content += 1
            # Content words decide; length only breaks ties between equals.
            score = run_content * 100 + run_len
            if run_content > 0 and score > best_score:
                best_score = score
                best_len = run_len
                best_start, best_end = run_start, i
        else:
            run_start = -1
            run_len = 0
            run_content = 0

    if best_score == 0:
        return -1, -1, 0
    return best_start, best_end, best_len


def segment_ayah(ayah_text: str, passage_texts: list[str]) -> list[Phrase]:
    """Derive the clause structure of an ayah from how it is quoted.

    Every bracketed quotation across the supplied commentaries is mapped to a
    span of the ayah's words. Spans are then merged: a span contained in another
    is folded into it, so the result is the coarsest division the corpus
    supports rather than a fragment for every passing gloss.

    With no quotations at all, the whole ayah is returned as a single phrase —
    an honest fallback, since nothing in the evidence divides it.
    """
    words = ayah_words(ayah_text)
    if not words:
        return []

    from tafahhum.arabic.normalize import strip_waqf_marks

    display_words = re.sub(r"\s+", " ", strip_waqf_marks(ayah_text).strip()).split()

    # Count how often each span is quoted.
    support: dict[tuple[int, int], int] = {}
    for text in passage_texts:
        seen_in_passage: set[tuple[int, int]] = set()
        for quotation in extract_quotations(text):
            q_words = quotation.split()
            if len(q_words) < MIN_PHRASE_WORDS:
                continue
            span = _find_span(q_words, words)
            if span and span[1] >= span[0]:
                seen_in_passage.add(span)
        for span in seen_in_passage:
            support[span] = support.get(span, 0) + 1

    if not support:
        return [
            Phrase(
                index=0, start_word=0, end_word=len(words) - 1,
                text=" ".join(display_words), normalized=" ".join(words), support=0,
            )
        ]

    # Rank by how many commentaries quoted the span, not by how long it is.
    #
    # Ranking by length lets a single passage that quotes half the ayah swallow
    # the tighter clauses inside it, which is exactly wrong: the divisions worth
    # showing are the ones the tradition returns to, and those are the
    # well-supported ones. Among equally supported spans the shorter wins, since
    # a tight clause is a more useful reading unit than a long one.
    ranked = sorted(support.items(), key=lambda kv: (-kv[1], kv[0][1] - kv[0][0]))

    accepted: list[tuple[int, int, int]] = []
    for (start, end), count in ranked:
        if count < MIN_PHRASE_SUPPORT:
            continue
        # Non-overlapping only. Overlapping divisions would put the same words
        # under two headings and double-count the commentary on them.
        if any(start <= b and a <= end for a, b, _ in accepted):
            continue
        accepted.append((start, end, count))

    if not accepted:
        accepted = [(0, len(words) - 1, 0)]

    # Every word of the ayah must belong to exactly one phrase — a reader must
    # never find a clause missing from the reading view.
    #
    # Words left between accepted spans are absorbed into the neighbouring
    # clause rather than emitted on their own. A gap is a remainder, not a
    # division: nobody quoted "نوم" by itself, and showing it as a heading with
    # no commentary under it would invent a clause the tradition does not have.
    accepted.sort(key=lambda s: s[0])
    covered: list[tuple[int, int, int]] = []
    for i, (start, end, count) in enumerate(accepted):
        # Absorb the gap before the first span, and after every span up to the
        # next one, so boundaries fall only where the corpus puts them.
        left = 0 if i == 0 else covered[-1][1] + 1
        right = accepted[i + 1][0] - 1 if i + 1 < len(accepted) else len(words) - 1
        covered.append((min(left, start), max(end, right), count))

    phrases: list[Phrase] = []
    for i, (start, end, count) in enumerate(covered):
        if end < start:
            continue
        phrases.append(
            Phrase(
                index=i,
                start_word=start,
                end_word=end,
                text=" ".join(display_words[start : end + 1]),
                normalized=" ".join(words[start : end + 1]),
                support=count,
            )
        )
    return phrases


def align_passage(
    passage_id: str,
    passage_text: str,
    ayah_text: str,
    phrases: list[Phrase],
) -> Alignment | None:
    """Decide which phrase a passage is commenting on.

    A bracketed quotation is preferred and recorded as such. Failing that, the
    longest run of ayah words in the passage is used, which is weaker evidence
    and is labelled so the interface can say how the link was established.
    """
    if not phrases:
        return None

    words = ayah_words(ayah_text)

    # Strong: the passage brackets a clause.
    best_span: tuple[int, int] | None = None
    best_len = 0
    for quotation in extract_quotations(passage_text):
        q_words = quotation.split()
        if len(q_words) < MIN_PHRASE_WORDS:
            continue
        span = _find_span(q_words, words)
        if span:
            length = span[1] - span[0] + 1
            if length > best_len:
                best_len = length
                best_span = span

    basis = "quoted"
    if best_span is None:
        start, end, length = _longest_common_run(
            normalize_for_matching(passage_text).split(), words
        )
        if length < 2:
            return None
        best_span, best_len, basis = (start, end), length, "overlap"

    # The phrase with the greatest overlap wins.
    start, end = best_span
    best_phrase, best_overlap = None, 0
    for phrase in phrases:
        overlap = min(end, phrase.end_word) - max(start, phrase.start_word) + 1
        if overlap > best_overlap:
            best_overlap = overlap
            best_phrase = phrase

    if best_phrase is None or best_overlap <= 0:
        return None

    confidence = 0.9 if basis == "quoted" else 0.55
    confidence *= min(1.0, best_overlap / max(1, best_phrase.word_count))

    return Alignment(
        passage_id=passage_id,
        phrase_index=best_phrase.index,
        basis=basis,
        matched_words=best_overlap,
        confidence=round(confidence, 3),
        opens_discussion=opens_discussion(passage_text),
    )


#: How far into a passage an opening marker may appear. Beyond this the passage
#: has already been saying something else, and the marker is a cross-reference.
OPENING_WINDOW = 160


def opens_discussion(passage_text: str) -> bool:
    """Whether a passage begins treating a clause, rather than continuing one.

    An opening announces itself the way the genre does: a lemma header, or the
    clause quoted in brackets, at the very start. A chunk that merely mentions
    the words further in is a continuation, and reads as a fragment if shown as
    though it were the commentator's treatment of the clause.
    """
    head = re.sub(r"\s+", " ", passage_text.strip())[:OPENING_WINDOW]
    if _HEADER_RE.search(head):
        return True
    return bool(_QUOTED.search(head))


# ---------------------------------------------------------------------------
# Passage gist
# ---------------------------------------------------------------------------

def passage_gist(passage_text: str, *, limit: int = 180) -> str:
    """A short opening line so a reader can scan before committing to read.

    Extracted, never written: the lemma header and its quotation are stripped,
    because they repeat what the phrase heading already says, and the first real
    clause of the commentary is returned. If that leaves nothing, the passage
    opens with something other than commentary and the raw opening is used.
    """
    text = re.sub(r"\s+", " ", passage_text.strip())

    # Drop a leading lemma header and the quotation that follows it.
    header = _HEADER_RE.match(text)
    if header:
        text = text[header.end():].lstrip(" :،")
    text = re.sub(r"^﴿[^﴾]*﴾\s*[:،]?\s*", "", text)
    text = re.sub(r"^\[\[.*?\]\]\s*", "", text)

    if not text.strip():
        text = re.sub(r"\s+", " ", passage_text.strip())

    # Cut at the first sentence boundary that leaves something readable.
    for mark in ("۔", ".", "،"):
        idx = text.find(mark, 40)
        if 0 < idx <= limit:
            return text[: idx + 1].strip()

    return (text[:limit].rstrip() + "…") if len(text) > limit else text.strip()
