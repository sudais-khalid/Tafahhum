# Language Pipeline

## Arabic is the pivot

```
user query (ar | en | ur)
      |  detect
      |  carry into Arabic
   RETRIEVAL  - always Arabic, always against Arabic sources
      |
   evidence package (Arabic passages, untouched)
      |  render interface in user language
   response
```

Arabic is the pivot because the corpus is Arabic. The alternative, translating a
million passages of classical Tafsir into English and retrieving over that, would
place a machine translation between the reader and every source. That is exactly
what this system exists to avoid.

## Source text is never silently translated

An Arabic passage is displayed in Arabic in all three interface languages. A
translation, where one exists, is:

- stored separately in `passage_translation`
- attributed to a translator, human or named model
- labelled as a translation
- shown beside the original, never in place of it
- never used as the text of a citation

The interface chrome is translated. The evidence is not.

## Detection

Arabic and Urdu share a script, so a script check cannot separate them. The
discriminator is Urdu's letter inventory (ٹ ڈ ڑ ں ے ہ ھ گ چ پ ژ), which standard
Arabic orthography does not use. Presence is close to conclusive; absence falls
back to function-word matching.

Detection is rule-based rather than model-based: it runs on every query, must be
reproducible so a logged classification can be replayed, and separates only three
classes.

Where the script is Arabic and no marker appears, the fallback is Arabic. A
misrouted Arabic query still retrieves; a misrouted Urdu query gets translated
unnecessarily.

## Query translation: a domain lexicon

The default translator maps technical vocabulary rather than translating prose.
For retrieval terms that is often the better tool:

    "occasion of revelation"  ->  سبب النزول

A general translator frequently produces a literal rendering that appears nowhere
in classical Tafsir. The lexicon hits the term the corpus actually uses.

Properties:

- deterministic, so a query run is reproducible
- offline, no external call on the hot path
- multi-word entries matched first, so "occasion of revelation" is not consumed
  as "revelation"
- Arabic already in the query is preserved verbatim, since a quoted Arabic phrase
  inside an English question is the strongest available signal
- when nothing maps, the user is told, rather than left with silent
  under-retrieval

## Swapping in a model translator

`Translator` is a Protocol; `set_translator()` installs any implementation.
Nothing downstream changes, because retrieval consumes `PivotResult.pivot_text`
and does not care how it was produced.

A model-backed translator is the right upgrade for full-sentence queries. It
should run *in addition to* the lexicon, not instead of it, so the technical term
is guaranteed present.

## Urdu specifics

Urdu queries keep their original script *and* gain mapped Arabic terms, because
Urdu religious writing already contains Arabic technical vocabulary the index can
match directly.

Urdu is set in Nastaliq in the interface. Setting Urdu in Naskh is legible but
reads as foreign to an Urdu reader.
