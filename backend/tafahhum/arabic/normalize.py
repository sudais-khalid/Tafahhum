"""Arabic text normalisation.

Normalisation exists so that two spellings of the same word compare equal during
retrieval. It is deliberately *lossy* and its output is never displayed to a user
and never stored as the text of a passage: `raw_text` and `verified_text` carry the
historical orthography, and `normalized_text` exists only to be matched against.

The distinction matters. Collapsing ``أ إ آ`` to ``ا`` is correct for a search index
and destructive for a printed edition, where the hamza carries the reading. Every
transformation here is therefore reversible only in the sense that the original is
still on disk beside it.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

# --------------------------------------------------------------------------
# Character classes
# --------------------------------------------------------------------------

# Harakat and Quranic annotation marks (U+064B–U+065F, U+0670, U+06D6–U+06ED).
# U+0640 (tatweel) is handled separately: it is a justification glyph, not a mark.
_DIACRITICS = re.compile(
    "["
    "ً-ٟ"   # fathatan .. wavy hamza below
    "ٰ"          # superscript alef
    "ۖ-ۜ"   # small high ligatures (Quranic)
    "۟-ۨ"   # small high marks
    "۪-ۭ"   # empty centre marks, small low meem
    "࣓-ࣿ"   # extended Arabic marks
    "︀-️"   # variation selectors
    "]"
)

_TATWEEL = "ـ"

# Quranic pause marks (waqf) — printed in the mushaf, not part of the word stream.
_WAQF_MARKS = re.compile("[ۖ-ۭ࣢]")

# Alef forms that collapse to bare alef for matching.
_ALEF_FORMS = str.maketrans({
    "آ": "ا",  # آ  alef with madda
    "أ": "ا",  # أ  alef with hamza above
    "إ": "ا",  # إ  alef with hamza below
    "ٱ": "ا",  # ٱ  alef wasla
    "ٲ": "ا",
    "ٳ": "ا",
    "ٵ": "ا",
})

# Other orthographic variants.
_LETTER_VARIANTS = str.maketrans({
    "ى": "ي",  # ى  alef maqsura -> ya
    "ی": "ي",  # ی  farsi ya -> ya
    "ة": "ه",  # ة  ta marbuta -> ha
    "ؤ": "و",  # ؤ  waw with hamza -> waw
    "ئ": "ي",  # ئ  ya with hamza -> ya
    "ك": "ك",  # ك  kaf (identity, kept for clarity)
    "ک": "ك",  # ک  keheh (Persian/Urdu) -> kaf
    "ں": "ن",  # ں  noon ghunna (Urdu) -> noon
    "ہ": "ه",  # ہ  heh goal (Urdu) -> heh
    "ۃ": "ه",
    "ە": "ه",
})

# Standalone hamza is dropped for matching; it is inconsistently written.
_HAMZA = "ء"

# Arabic-Indic and extended Arabic-Indic digits -> ASCII.
_DIGITS = str.maketrans(
    "٠١٢٣٤٥٦٧٨٩"
    "۰۱۲۳۴۵۶۷۸۹",
    "01234567890123456789",
)

# Arabic punctuation -> ASCII equivalents, so tokenisation is uniform.
_PUNCT = str.maketrans({
    "،": ",",   # ،
    "؛": ";",   # ؛
    "؟": "?",   # ؟
    "٪": "%",
    "٫": ".",
    "٬": ",",
    "٭": "*",
    "۔": ".",   # ۔ Urdu full stop
    "‐": "-", "‑": "-", "‒": "-", "–": "-", "—": "-",
    "“": '"', "”": '"', "‘": "'", "’": "'",
    "«": '"', "»": '"',
})

_WHITESPACE = re.compile(r"\s+")

# Ornamental characters that appear in printed editions but carry no text.
_ORNAMENTS = re.compile(
    "["
    "۞"          # start of rub el hizb
    "۩"          # place of sajdah
    "﴾﴿"    # ornate parentheses
    "​-‏"   # zero-width and directional marks
    "‪-‮"   # embedding/override
    "⁦-⁩"   # isolates
    "]"
)

ARABIC_LETTERS = re.compile(r"[ء-غف-يٱ-ۓ]")


# --------------------------------------------------------------------------
# Operations
# --------------------------------------------------------------------------

def strip_diacritics(text: str) -> str:
    """Remove harakat, Quranic annotation, and tatweel."""
    return _DIACRITICS.sub("", text).replace(_TATWEEL, "")


def strip_waqf_marks(text: str) -> str:
    """Remove Quranic pause marks while leaving harakat intact."""
    return _WAQF_MARKS.sub("", text)


def unify_alef(text: str) -> str:
    """Collapse all alef forms to bare alef."""
    return text.translate(_ALEF_FORMS)


def unify_letters(text: str) -> str:
    """Collapse orthographic letter variants, including Urdu/Persian forms."""
    return text.translate(_LETTER_VARIANTS)


def normalize_digits(text: str) -> str:
    """Convert Arabic-Indic digits to ASCII."""
    return text.translate(_DIGITS)


def normalize_punctuation(text: str) -> str:
    """Convert Arabic punctuation to ASCII equivalents."""
    return text.translate(_PUNCT)


def strip_ornaments(text: str) -> str:
    """Remove printing ornaments and bidirectional control characters."""
    return _ORNAMENTS.sub("", text)


def collapse_whitespace(text: str) -> str:
    return _WHITESPACE.sub(" ", text).strip()


def is_arabic_script(text: str) -> bool:
    """True when the text contains at least one Arabic-script letter."""
    return ARABIC_LETTERS.search(text) is not None


def arabic_ratio(text: str) -> float:
    """Fraction of alphabetic characters that are Arabic script.

    Used by language detection to distinguish an Arabic query from a romanised one.

    Tatweel is excluded from the denominator: Unicode classifies it as a modifier
    letter, but it is a justification glyph carrying no linguistic content, and
    counting it would drag the ratio of fully-Arabic text below 1.0.
    """
    letters = [c for c in text if c.isalpha() and c != _TATWEEL]
    if not letters:
        return 0.0
    arabic = sum(1 for c in letters if ARABIC_LETTERS.match(c))
    return arabic / len(letters)


# --------------------------------------------------------------------------
# Pipelines
# --------------------------------------------------------------------------

def normalize_for_display(text: str) -> str:
    """Minimal cleanup that preserves orthography.

    Applied to text on its way to a reader: Unicode is put in a canonical
    composition, invisible control characters are dropped, and whitespace is
    tidied. Diacritics, hamza forms, and alef forms are all preserved, because
    they are part of what the edition actually prints.
    """
    text = unicodedata.normalize("NFC", text)
    text = strip_ornaments(text)
    return collapse_whitespace(text)


def normalize_for_matching(text: str) -> str:
    """Aggressive normalisation for the search index.

    Order matters: diacritics are stripped before letter unification so that a
    superscript alef does not survive into the alef-collapsing step, and hamza is
    dropped last so that hamza-bearing carriers are folded onto their base letter
    first.
    """
    text = unicodedata.normalize("NFC", text)
    text = strip_ornaments(text)
    text = strip_diacritics(text)
    text = unify_alef(text)
    text = unify_letters(text)
    text = text.replace(_HAMZA, "")
    text = normalize_digits(text)
    text = normalize_punctuation(text)
    return collapse_whitespace(text)


def normalize_key(text: str) -> str:
    """Matching form with punctuation removed entirely.

    Used for name and title lookup, where punctuation is noise: the same Mufassir
    may be written with or without commas, brackets, or a bracketed death date.
    """
    text = normalize_for_matching(text)
    text = re.sub(r"[^\w\sء-ۿ]", " ", text)
    return collapse_whitespace(text.lower())


@dataclass(frozen=True)
class NormalizedText:
    """The three representations, carried together."""

    original: str
    display: str
    matching: str

    @classmethod
    def of(cls, text: str) -> NormalizedText:
        return cls(
            original=text,
            display=normalize_for_display(text),
            matching=normalize_for_matching(text),
        )
