# Data Model

21 tables in PostgreSQL 17. This document records *why* the schema is shaped as
it is; the schema itself lives in `backend/migrations/`.

## Three layers

```
BIBLIOGRAPHY          CORPUS                  RETRIEVAL
mufassir              scan_page               search_vector (generated)
tafsir_work           passage                 embedding vector(1024)
edition               passage_ayah            GiST range index
biblio_source         passage_correction
*_attestation         passage_translation
```

Bibliography describes what exists. Corpus holds what has been ingested.
Retrieval is derived and can be rebuilt from corpus at any time.

## Decisions worth recording

### Work and edition are separate entities

A citation to "al-Tabari, 3/241" is meaningless without knowing which printing.
Editions differ in volume count, pagination, editorial apparatus, and legal
status. Passages attach to an `edition_id`, never to a work alone.

### `passage_ayah` is a join table, not a column pair

A Mufassir may treat 2:255 and 2:256 together, or cite 2:255 while commenting
elsewhere. An `ayah_start`/`ayah_end` pair on `passage` expresses the first case
and not the second. The join table also carries an `alignment` kind, so "this
passage *is* the commentary on 2:255" is distinguishable from "this passage
mentions 2:255 in passing".

Indexed with GiST range overlap, so a search for 2:256 finds a passage aligned to
2:255-257.

### Three text columns, never collapsed

| Column | Purpose | Mutable |
|---|---|---|
| `raw_text` | Exactly what OCR or the source produced | Never, trigger-enforced |
| `normalized_text` | Matching form; what the FTS index sees | Derived, recomputable |
| `verified_text` | Human-approved reading | Reviewer only, logged |

`raw_text` immutability is a row trigger, not a convention. A correction writes
`verified_text` and appends to `passage_correction`, so every change stays
reversible and attributable.

### `published_passage` is a view, not a WHERE clause

Fixture and unverified exclusion lives in the database. A new query path that
forgets its filter returns nothing rather than leaking test data. The failure
mode is visible instead of silent.

### Confidence is multi-dimensional

There is no `accuracy_score`. `ocr_confidence`, `verification_status`,
`citation_precision`, and `attribution_confidence` are separate columns because
they answer different questions. A passage can have perfect OCR and disputed
attribution; averaging them erases exactly the information a researcher needs.

### Hijri dates are authoritative

`death_year_hijri` is the sort key for historical queries. Gregorian columns are
derived and approximate. `historical_period` is a filtering convenience and
asserts no periodisation scheme.

### Why not Neo4j, yet

The graph queries needed are one or two hops: `mufassir -> wrote -> tafsir_work
-> explains -> ayah`. That is a join. A graph database earns its place when a
query needs variable-depth traversal, and transitive isnad chains across
generations are the realistic candidate. Until such a query exists and is slow,
adjacency tables in PostgreSQL are correct.

### Why not OpenSearch, yet

PostgreSQL full-text search with a custom Arabic configuration currently meets
recall targets. A second search system means a second index to keep consistent
with the corpus. That cost is worth paying when measured recall demands it, and
not before.

## Enum parity

Python enums in `tafahhum/core/enums.py` mirror the PostgreSQL enum types. A
mismatch surfaces as a cast error deep inside a query rather than at import, so
they must be changed together.
