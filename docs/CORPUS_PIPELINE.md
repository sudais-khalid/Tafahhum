# Corpus Pipeline

## States

```
DISCOVERED -> ACQUIRED -> SCANNED -> OCR_COMPLETE -> NORMALIZED
  -> AYAH_ALIGNED -> METADATA_COMPLETE -> HUMAN_REVIEW -> VERIFIED
  -> INDEXED -> PUBLISHED
```

Only PUBLISHED works are visible to users by default. VERIFIED means a human
reviewer approved the text against a page image, not that a heuristic passed.

## Two ingestion paths

### Path A: digital text (implemented)

```
Digital text source
  -> chunk on structural boundaries
  -> normalise
  -> ayah alignment (structural, from the source layout)
  -> passages with edition, without volume or page
```

What this path can support: the text, attributed to a named work and author, and
ayah alignment.

What it cannot support, and therefore must not assert: volume and page numbers,
the identity of the print edition keyed from, and biographical data for the
author. Those fields stay NULL and `citation_precision` stays UNVERIFIED. The
provenance ladder in the interface shows two of five dots filled, so the reader
sees the limitation on every passage.

### Path B: print edition with scans (Phase 5)

```
Physical book
  -> high-resolution scan          (page images retained permanently)
  -> OCR                           (raw output never overwritten)
  -> Arabic normalisation
  -> error detection               (low confidence flagged for review)
  -> human verification            (writes verified_text, logs a correction)
  -> ayah alignment
  -> metadata assignment
  -> indexing
```

The page image is the primary visual evidence and is never discarded.

## Chunking

A commentary on one ayah can exceed 32,000 characters. That is too coarse to
retrieve: a query about one clause returns the whole discussion, and an embedding
of the block averages a dozen unrelated topics.

Chunking is a retrieval decision, made structurally rather than by character
count. Classical Tafsir has visible internal structure: the القول في تأويل قوله
تعالى headers that open a lemma, the separators between transmitted reports, and
paragraph breaks. Splitting there keeps a chunk to one argument, which is what a
citation should point at.

Targets: ~1200 characters, maximum ~2200, minimum ~120. A single sentence longer
than the maximum is left intact rather than cut mid-clause, because an unreadable
fragment is worse than an oversized passage. Chunks never cross an ayah boundary.

Result on al-Tabari's commentary on 2:255: 31 passages, median 1116 characters.

## Corrections are additive

`raw_text` is immutable, enforced by trigger. A correction writes `verified_text`
and appends a `passage_correction` row with the previous text, the reason, and
the reviewer. Nothing is ever overwritten, so any correction can be traced and
reversed.

## Seeding a development corpus

```bash
python scripts/fetch_corpus.py
```

Fetches and ingests a bounded slice: 10 works across 21 ayahs. This is a
development tool, not the production path. The production path starts from an
identified print edition and its scans.
