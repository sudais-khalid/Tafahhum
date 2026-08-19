# Architecture

## 1. The invariant

```
SOURCE → STRUCTURE → RETRIEVE → VERIFY → SYNTHESIZE → CITE
```

Every layer below exists to enforce that order. The generation layer is deliberately
the *last* and *least privileged* component in the system: it receives a sealed
evidence package and may not reach back into the corpus.

## 2. Layer map

```
                          TAFAHHUM
                              │
                        USER QUESTION  (ar | en | ur)
                              │
                              ▼
                    ┌───────────────────┐
                    │ LANGUAGE PIPELINE │   detect → pivot(ar) → normalise
                    └───────────────────┘
                              │
                              ▼
                    ┌───────────────────┐
                    │ QUERY UNDERSTANDING│  ayah refs, entities, classification
                    └───────────────────┘
                              │
                              ▼
                    ┌───────────────────┐
                    │ SCHOLARLY RULES   │   provenance-bearing, deterministic
                    └───────────────────┘
                              │
             ┌────────────────┼────────────────┐
             ▼                ▼                ▼
        Exact / BM25      Dense vector      Graph walk
        (sparse)          (semantic)        (relations)
             └────────────────┼────────────────┘
                              ▼
                         ┌─────────┐
                         │ RERANK  │
                         └─────────┘
                              ▼
                    ┌───────────────────┐
                    │ EVIDENCE ASSEMBLY │   sealed package, nothing else passes
                    └───────────────────┘
                              ▼
                    ┌───────────────────┐
                    │ SOURCE VALIDATOR  │   passage↔citation integrity
                    └───────────────────┘
                              ▼
                    ┌───────────────────┐
                    │ CONTROLLED GEN    │   organise · attribute · cite
                    └───────────────────┘
                              ▼
                    ┌───────────────────┐
                    │ CITATION VERIFY   │   every claim → evidence or removed
                    └───────────────────┘
                              ▼
                    ┌───────────────────┐
                    │ PRESENTATION      │   render into user language
                    └───────────────────┘
                              ▼
                           RESPONSE
```

## 3. Why the generation layer is sandboxed

The single largest failure mode for a system like this is a fluent, well-formed answer
that cites a page which does not say what the answer claims. Three structural defences:

1. **No corpus access from generation.** The generator is a pure function of the
   evidence package. It cannot retrieve, so it cannot silently widen its own evidence.
2. **Citation identifiers are opaque and pre-minted.** The generator references
   evidence by `passage_id` handed to it. It has no mechanism to *construct* a
   citation, so a fabricated page number is not expressible.
3. **Post-generation verification.** Claims are extracted from the produced text and
   re-matched against the evidence package. Unsupported claims are removed or flagged
   before the answer is ever shown.

If the evidence set is empty, the correct output is
*"Insufficient verified evidence was retrieved from the current corpus."*
That is a success state, not a failure state.

## 4. Module boundaries (backend)

| Package | Responsibility | May depend on |
|---|---|---|
| `tafahhum.core` | Config, types, errors, enums | — |
| `tafahhum.arabic` | Normalisation, diacritics, tokens, roots | `core` |
| `tafahhum.language` | Detection, pivot translation, presentation | `core`, `arabic` |
| `tafahhum.quran` | Surah metadata, ayah reference parsing | `core`, `arabic` |
| `tafahhum.db` | Connection, migrations, repositories | `core` |
| `tafahhum.corpus` | Ingestion, OCR, alignment, verification state | `core`, `arabic`, `db` |
| `tafahhum.retrieval` | Sparse, dense, hybrid fusion, reranking | `core`, `arabic`, `db` |
| `tafahhum.rules` | Query classification, rule engine | `core`, `quran`, `db` |
| `tafahhum.evidence` | Evidence assembly, validation, citation check | `core`, `db`, `retrieval` |
| `tafahhum.generation` | Controlled response construction | `core`, `evidence`, `language` |
| `tafahhum.api` | HTTP surface | all of the above |

Dependencies point strictly downward. `retrieval` never imports `generation`.
This is what makes the response model replaceable (§37) — swapping the generator
touches exactly one package.

## 5. Storage

**PostgreSQL 17 + pgvector** is the single system of record for the MVP:

- relational corpus and metadata
- `tsvector` full-text search with an Arabic-aware configuration
- `vector` columns for dense retrieval
- adjacency tables for the knowledge graph

A dedicated graph database is deliberately *not* introduced yet. The graph queries the
MVP needs are 1–2 hops (`mufassir → wrote → tafsir → explains → ayah`), which is a join,
not a traversal problem. Neo4j earns its place only when a query genuinely needs
variable-depth traversal — e.g. transitive teacher/student isnād chains across many
generations. That justification is recorded in `docs/DATA_MODEL.md` rather than assumed.

Likewise OpenSearch is not introduced while PostgreSQL full-text search meets recall
targets on the benchmark. Every piece of infrastructure must solve a measured problem.

## 6. Text representation — three parallel columns

Every textual artefact carries three representations, never collapsed:

| Column | Meaning | Mutable |
|---|---|---|
| `raw_text` | Exactly what the OCR or source produced | **Never** |
| `normalized_text` | Machine-comparable form (see ARABIC_PROCESSING.md) | Derived, recomputable |
| `verified_text` | Human-approved reading | By reviewer only, audited |

Retrieval indexes `normalized_text`. Display prefers `verified_text`, falling back to
`raw_text`. Corrections are *additive*: `raw_text` is preserved so that any correction
remains traceable and reversible.

## 7. Where scholarly judgement lives

The system makes **no** scholarly judgements of its own. It makes retrieval decisions,
and every retrieval decision is explainable by a rule that itself carries a citation to
a scholarly source. See `docs/RULE_ENGINE.md`.

Retrieval rank is not scholarly authority. The system never resolves a disagreement
between Mufassirun by counting passages or comparing similarity scores.
