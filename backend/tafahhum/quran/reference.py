"""Parsing Quranic references out of free text, in Arabic, English, or Urdu.

A user may write the same reference as any of:

    2:255 · 2/255 · Q2.255 · ٢:٢٥٥ · Surah 2 ayah 255 · Al-Baqarah 255
    سورة البقرة الآية ٢٥٥ · البقرة ٢٥٥ · سورہ بقرہ آیت ۲۵۵ · Ayat al-Kursi

All of those must resolve to the same location. Parsing runs before retrieval and
before question classification, because the presence of a resolved ayah is itself a
strong classification signal.

Every reference is validated against the real ayah count of the surah, so
``2:300`` is rejected rather than silently retrieving nothing.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from tafahhum.arabic.normalize import normalize_digits, normalize_key
from tafahhum.quran.surah_data import SURAH_BY_NUMBER, SURAHS, Surah


@dataclass(frozen=True, order=True)
class AyahRef:
    """A contiguous run of ayahs within one surah."""

    surah: int
    start: int
    end: int

    def __post_init__(self) -> None:
        if self.end < self.start:
            raise ValueError(f"invalid range {self.surah}:{self.start}-{self.end}")

    @property
    def is_single(self) -> bool:
        return self.start == self.end

    @property
    def surah_meta(self) -> Surah:
        return SURAH_BY_NUMBER[self.surah]

    def __str__(self) -> str:
        if self.is_single:
            return f"{self.surah}:{self.start}"
        return f"{self.surah}:{self.start}-{self.end}"

    def label(self, language: str = "en") -> str:
        meta = self.surah_meta
        name = meta.name_ar if language == "ar" else meta.name_en_translit
        span = str(self.start) if self.is_single else f"{self.start}-{self.end}"
        return f"{name} {self.surah}:{span}"


@dataclass
class ParseResult:
    refs: list[AyahRef] = field(default_factory=list)
    #: Text with recognised references removed — the residue is the topical part
    #: of the query, and is what gets embedded for semantic retrieval.
    residual_text: str = ""
    matched_spans: list[tuple[int, int, str]] = field(default_factory=list)

    @property
    def has_reference(self) -> bool:
        return bool(self.refs)


# ---------------------------------------------------------------------------
# Surah name index
# ---------------------------------------------------------------------------

# Definite-article prefixes, including sun-letter assimilations, that appear in
# transliterated surah names. Stripped so "An-Naas", "Naas", and "al-nas" agree.
_LATIN_ARTICLES = {
    "al", "an", "ar", "as", "ash", "at", "az", "ad", "adh", "ath", "a",
}


def _fold_latin(text: str) -> str:
    """Collapse the spelling variation transliteration schemes introduce."""
    folded = re.sub(r"(.)\1+", r"\1", text)   # faatiha -> fatiha
    return re.sub(r"h$", "", folded)          # baqarah -> baqara


def _latin_key(name: str) -> str:
    """Fold a transliterated name to a comparison key.

    Transliteration is not standardised: vowel length is written doubled
    ("Faatiha") or single ("Fatiha"), final ta marbuta is written "-a" or "-ah",
    and the article may be hyphenated, spaced, or absent. Collapsing repeated
    letters and dropping a trailing "h" makes those variants converge.

    The article is only stripped when a separator makes it unambiguous. In
    "Albaqarah" the leading "al" cannot be told from part of the name, so the
    key keeps it and the index carries both forms instead of guessing here.
    """
    parts = re.split(r"[\s\-_']+", name.lower())
    parts = [re.sub(r"[^a-z]", "", p) for p in parts]
    parts = [p for p in parts if p]
    if len(parts) > 1 and parts[0] in _LATIN_ARTICLES:
        parts = parts[1:]
    return _fold_latin("".join(parts))


def _latin_key_with_article(name: str) -> str:
    """The same key, but retaining a leading definite article."""
    cleaned = re.sub(r"[^a-z]", "", name.lower())
    return _fold_latin(cleaned)


def _arabic_keys(name_plain: str) -> set[str]:
    """Keys for an Arabic surah name, with and without the definite article."""
    keys = {name_plain}
    if name_plain.startswith("ال") and len(name_plain) > 3:
        keys.add(name_plain[2:])
    return keys


def _build_name_index() -> tuple[dict[str, int], dict[str, int], dict[str, int]]:
    """Build three lookup tables.

    Transliterations and English translations are kept apart deliberately. Many
    surah translations are ordinary English nouns — "Man", "Light", "The Cow",
    "Iron" — so allowing them into the *bare* name-plus-number pattern would make
    "a man 5 times" parse as 76:5. Translations are therefore only consulted when
    the user wrote an explicit "surah" keyword.
    """
    translit: dict[str, int] = {}
    latin_all: dict[str, int] = {}
    arabic: dict[str, int] = {}

    # Article-stripped keys are registered for every surah first, so that one
    # surah's with-article spelling can never shadow another's canonical name.
    for s in SURAHS:
        key = _latin_key(s.name_en_translit)
        if key:
            translit.setdefault(key, s.number)
            latin_all.setdefault(key, s.number)
    for s in SURAHS:
        key = _latin_key_with_article(s.name_en_translit)
        if key:
            translit.setdefault(key, s.number)
            latin_all.setdefault(key, s.number)
    for s in SURAHS:
        key = _latin_key(s.name_en)
        if key:
            latin_all.setdefault(key, s.number)
        for akey in _arabic_keys(s.name_ar_plain):
            if akey:
                arabic.setdefault(akey, s.number)
    return translit, latin_all, arabic


_LATIN_TRANSLIT_INDEX, _LATIN_NAME_INDEX, _ARABIC_NAME_INDEX = _build_name_index()

# Longest names first, so "ali imran" is not shadowed by a shorter prefix match.
_ARABIC_NAMES_BY_LENGTH = sorted(_ARABIC_NAME_INDEX, key=len, reverse=True)


# ---------------------------------------------------------------------------
# Well-known named passages
#
# These are conventional identifications, widely used as finding aids. They are
# marked UNVERIFIED in the database (`ayah_alias`) and are a navigational
# convenience only — resolving a name to a location makes no interpretive claim
# about the passage.
# ---------------------------------------------------------------------------
_ALIASES: dict[str, AyahRef] = {}


def _register_alias(names: list[str], ref: AyahRef) -> None:
    for n in names:
        _ALIASES[normalize_key(n)] = ref
        _ALIASES[_latin_key(n)] = ref


_register_alias(
    ["Ayat al-Kursi", "Ayatul Kursi", "آية الكرسي", "آیت الکرسی", "aayat ul kursi"],
    AyahRef(2, 255, 255),
)
_register_alias(["Al-Fatiha", "Surah Fatiha", "سورة الفاتحة"], AyahRef(1, 1, 7))
_register_alias(["Al-Ikhlas", "سورة الإخلاص"], AyahRef(112, 1, 4))


# ---------------------------------------------------------------------------
# Patterns
# ---------------------------------------------------------------------------

# 2:255 | 2:255-257 | 2:255–257 | Q2.255 | 2/255
_NUMERIC = re.compile(
    r"\b(?:q|s)?\s*(\d{1,3})\s*[:./]\s*(\d{1,3})(?:\s*[-–—]\s*(\d{1,3}))?\b",
    re.IGNORECASE,
)

# "surah 2 ayah 255", "surah 2, verse 255"
_WORDY_NUMERIC = re.compile(
    r"\b(?:surah?|sura|chapter)\s*(\d{1,3})\s*[,:]?\s*"
    r"(?:ayah?|aayah|verse|ayat)\s*(\d{1,3})(?:\s*[-–—]\s*(\d{1,3}))?\b",
    re.IGNORECASE,
)

# Arabic/Urdu: سورة <name> الآية <n>  /  سورہ <name> آیت <n>
# The heh class covers ة (ta marbuta), ه (heh), and ہ (Urdu heh goal, U+06C1).
_AR_WORDY = re.compile(
    r"(?:سور[ةهہ])\s+([^\d]{2,25}?)\s*"
    r"(?:(?:ال)?[آا]ي[ةتهہ]|[آا]ی[تة])?\s*(\d{1,3})(?:\s*[-–—]\s*(\d{1,3}))?"
)

# Bare Arabic/Urdu name plus number: البقرة ٢٥٥
_AR_BARE = re.compile(
    r"([ؠ-ۿ]{3,20}(?:\s+[ؠ-ۿ]{2,20})?)\s+(\d{1,3})"
    r"(?:\s*[-–—]\s*(\d{1,3}))?\b"
)

# Bare transliterated name plus number: Al-Baqarah 255
_LATIN_BARE = re.compile(
    r"\b((?:al|an|ar|as|ash|at|az|ad)[\s\-']?[A-Za-z']{2,18}|[A-Za-z']{3,18})\s+"
    r"(\d{1,3})(?:\s*[-–—]\s*(\d{1,3}))?\b",
    re.IGNORECASE,
)

_STOPWORDS_AR = {"ال", "من", "في", "عن", "الكريمة", "الكريم", "رقم"}


def _clamp(surah: int, start: int, end: int | None) -> AyahRef | None:
    """Build a reference, rejecting anything outside the real mushaf."""
    meta = SURAH_BY_NUMBER.get(surah)
    if meta is None or start < 1 or start > meta.ayah_count:
        return None
    if end is None:
        end = start
    if end < start or end > meta.ayah_count:
        # A range that overruns the surah is truncated rather than dropped: the
        # user's intent ("from 255 onward") is still recoverable and useful.
        end = meta.ayah_count
    return AyahRef(surah, start, end)


def _resolve_surah_name(
    fragment: str, *, translit_only: bool = False, strict: bool = False
) -> int | None:
    """Resolve a surah name fragment in any of the three languages.

    `translit_only` restricts Latin matching to transliterated names, for use by
    the bare name-plus-number pattern where an English translation would produce
    false positives on ordinary nouns.

    `strict` disables the substring fallback. The fallback exists to tolerate
    honorifics and filler around a name that followed an explicit "surah"
    keyword; without that keyword it would make any Arabic word followed by a
    number resolve to whichever surah name happened to be a substring.
    """
    fragment = fragment.strip()
    if not fragment:
        return None

    latin = _latin_key(fragment)
    index = _LATIN_TRANSLIT_INDEX if translit_only else _LATIN_NAME_INDEX
    if latin in index:
        return index[latin]
    if translit_only:
        return None

    arabic = normalize_key(fragment)
    if arabic in _ARABIC_NAME_INDEX:
        return _ARABIC_NAME_INDEX[arabic]
    if strict:
        return None

    # Fall back to the longest known name contained in the fragment, which
    # tolerates the honorifics and filler words that surround a name in prose.
    tokens = [t for t in arabic.split() if t not in _STOPWORDS_AR]
    rebuilt = " ".join(tokens)
    for name in _ARABIC_NAMES_BY_LENGTH:
        if len(name) >= 3 and name in rebuilt:
            return _ARABIC_NAME_INDEX[name]
    return None


def parse_ayah_references(text: str) -> ParseResult:
    """Extract every Quranic reference from free text.

    References are matched most-specific-first so that a numeric form inside a
    wordy form is not double-counted, and each matched span is blanked before the
    next pattern runs.
    """
    if not text or not text.strip():
        return ParseResult(residual_text="")

    working = normalize_digits(text)
    found: list[AyahRef] = []
    spans: list[tuple[int, int, str]] = []

    def consume(pattern: re.Pattern[str], build) -> None:
        nonlocal working
        out = []
        last = 0
        for m in pattern.finditer(working):
            ref = build(m)
            if ref is None:
                continue
            found.append(ref)
            spans.append((m.start(), m.end(), m.group(0)))
            out.append(working[last:m.start()])
            out.append(" " * (m.end() - m.start()))
            last = m.end()
        out.append(working[last:])
        working = "".join(out)

    # 1. "surah 2 ayah 255"
    consume(
        _WORDY_NUMERIC,
        lambda m: _clamp(int(m.group(1)), int(m.group(2)),
                         int(m.group(3)) if m.group(3) else None),
    )

    # 2. Arabic/Urdu named form
    def _ar(m: re.Match[str]) -> AyahRef | None:
        surah = _resolve_surah_name(m.group(1))
        if surah is None:
            return None
        return _clamp(surah, int(m.group(2)),
                      int(m.group(3)) if m.group(3) else None)

    consume(_AR_WORDY, _ar)

    # 3. Bare numeric "2:255"
    consume(
        _NUMERIC,
        lambda m: _clamp(int(m.group(1)), int(m.group(2)),
                         int(m.group(3)) if m.group(3) else None),
    )

    # 4. Bare name plus number: "Al-Baqarah 255", "البقرة ٢٥٥".
    #    Both resolve strictly: a fragment that is not a known surah name yields
    #    no match, so ordinary prose containing a number is left alone.
    def _named(translit_only: bool):
        def build(m: re.Match[str]) -> AyahRef | None:
            surah = _resolve_surah_name(
                m.group(1), translit_only=translit_only, strict=True
            )
            if surah is None:
                return None
            return _clamp(surah, int(m.group(2)),
                          int(m.group(3)) if m.group(3) else None)
        return build

    consume(_AR_BARE, _named(translit_only=False))
    consume(_LATIN_BARE, _named(translit_only=True))

    # 5. Named passages, e.g. "Ayat al-Kursi"
    residual_latin = _latin_key(working)
    residual_arabic = normalize_key(working)
    for alias_key, ref in _ALIASES.items():
        if len(alias_key) < 5:
            continue
        if alias_key in residual_latin or alias_key in residual_arabic:
            if ref not in found:
                found.append(ref)
            break

    # Deduplicate, preserving first-seen order.
    unique: list[AyahRef] = []
    for r in found:
        if r not in unique:
            unique.append(r)

    return ParseResult(
        refs=unique,
        residual_text=re.sub(r"\s+", " ", working).strip(),
        matched_spans=spans,
    )


def format_reference_list(refs: list[AyahRef], language: str = "en") -> str:
    return "، ".join(r.label("ar") for r in refs) if language == "ar" \
        else ", ".join(r.label("en") for r in refs)
