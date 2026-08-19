# Roadmap

Phases are ordered so each one proves something the next depends on. Nothing is
scheduled by date; a phase ends when its exit criteria hold.

## Phase 0 — Foundation *(complete)*

Corpus schema, Arabic processing, multilingual reference parsing.

**Met:** 21 tables; integrity constraints reject an unsourced scholarly rule;
Arabic normalisation separates display from matching; references parse in Arabic,
English, and Urdu with false-positive guards.

## Phase 1 — First vertical slice *(complete)*

"What do the Tafasir say about 2:255?" returns real passages from ten works with
provenance, in any of the three languages.

**Met:** 2,432 passages ingested; hybrid retrieval with per-work partitioning;
rule engine with 16 structural rules; evidence assembly; query API; research
interface. 145 tests.

## Phase 2 — Dense retrieval

Embed the corpus and turn on the third retrieval strategy.

- BGE-M3 embeddings over `normalized_text`, batched and resumable
- HNSW tuning against a held-out query set
- Cross-encoder reranking over the fused candidate pool

**Exit:** dense retrieval measurably improves NDCG@10 on the thematic slice of
the benchmark, or is documented as not helping and left off. Shipping it because
it sounds advanced is not an outcome.

## Phase 3 — Bibliographical layer

The largest current gap. Every Mufassir in the corpus has a NULL death year: the
text source supplied only names, and nothing was invented to fill the space.

- Ingest a *tabaqat al-mufassirin* work as a first-class corpus source
- Extract entries into `mufassir_attestation` with volume and page
- Human review, then populate dates, places, and relations

Unlocks historical-mode ordering, period filters, and the teacher/student graph —
all of which are currently inert.

**Exit:** every published work's author carries a death year with an attestation
pointing to a specific page, or is explicitly marked disputed.

## Phase 4 — Scholarly rule engine

With a bibliographical source ingested and read, draft candidate methodological
rules, each anchored to a volume and page, and put them through human review.
See `SOURCE_POLICY.md` section 6 for the required path.

**Exit:** at least one SCHOLARLY_METHOD rule exists, VERIFIED, with a named
reviewer and a page reference, visible in `GET /api/v1/rules`.

## Phase 5 — Print editions and scans

The path from a digital text to a citable page.

- Scan ingestion, page-image storage, OCR with confidence retained
- Review queue for low-confidence pages
- Passage-to-page alignment, so the provenance ladder fills to its last dot
- Deep links from a citation to the scanned page

**Exit:** at least one work cited to volume and page against a scan a user can
open.

## Phase 6 — Controlled generation

Only after the evidence infrastructure is proven.

- Generation consumes the sealed evidence package and nothing else
- Claim extraction and citation verification before anything is shown
- Unsupported claims removed or flagged, never silently kept
- Answer modes: simple, detailed, comparative, research, source, historical

**Exit:** unsupported-claim rate measured on the benchmark and reported.

## Phase 7 — Corpus expansion

20 to 50 to 100 to 250 to 500 to 1000+. Adding a work must require ingestion and
verification, never architectural change. If it ever requires a schema change,
that is a design defect to fix before continuing.

## Phase 8 — Corpus management interface

Administrative surface for researchers: add works, upload scans, run and review
OCR, correct text, assign ayahs, verify passages, manage licences, publish.
Nobody should need to write SQL to maintain the corpus.
