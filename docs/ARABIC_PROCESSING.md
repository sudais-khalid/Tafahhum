# Arabic Processing

## Two pipelines, never confused

| Pipeline | Purpose | Loses information |
|---|---|---|
| `normalize_for_display` | text on its way to a reader | no |
| `normalize_for_matching` | text on its way to an index | yes, deliberately |

Collapsing أ إ آ ٱ to ا is correct for a search index and destructive for a
printed edition, where the hamza carries the reading. The two pipelines exist so
that decision is made once, explicitly, per destination.

`normalize_for_matching` output is never displayed and never stored as the text
of a passage.

## What matching normalisation does

1. NFC composition
2. strip printing ornaments and bidirectional controls
3. strip harakat, Quranic annotation marks, and tatweel
4. collapse alef forms: آ أ إ ٱ ٲ ٳ ٵ to ا
5. collapse letter variants: ى to ي, ة to ه, ؤ to و, ئ to ي, ک to ك, ں to ن, ہ to ه
6. drop standalone hamza
7. Arabic-Indic and extended Arabic-Indic digits to ASCII
8. Arabic punctuation to ASCII
9. collapse whitespace

Order matters: diacritics go before letter unification so a superscript alef does
not survive into the alef-collapsing step, and hamza is dropped last so
hamza-bearing carriers fold onto their base letter first.

Worked example:

    input   ٱللَّهُ لَاۤ إِلَـٰهَ إِلَّا هُوَ ٱلۡحَیُّ ٱلۡقَیُّومُۚ
    output  الله لا اله الا هو الحي القيوم

## Urdu and Persian letters

Matching normalisation folds ک ں ہ onto their Arabic equivalents. This is
intentional: it lets a name written in Urdu orthography match the same name in an
Arabic source. Detection runs on raw text, before normalisation, so this folding
does not interfere with telling Arabic from Urdu.

## Tatweel and `arabic_ratio`

Unicode classifies tatweel as a modifier letter, so `isalpha()` returns true for
it. Counting it drags the ratio of fully-Arabic text below 1.0, so it is excluded
from the denominator. It carries no linguistic content.

## Three representations, carried together

`NormalizedText.of(text)` returns original, display, and matching forms together,
mirroring the three columns on `passage`.
