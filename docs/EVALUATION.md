# Evaluation

## Principle

Do not judge the system by how natural its generated answers sound. Fluency is
uncorrelated with citation accuracy, and a fluent wrong answer is the failure
mode that matters.

## Benchmark categories

```
Ayah retrieval            Arabic exact search        Citation accuracy
Tafsir retrieval          Semantic search            Attribution accuracy
Mufassir retrieval        Comparative Tafsir         Rule compliance
Historical search         Disagreement detection     Unsupported claim detection
```

## Metrics

| Metric | Measures |
|---|---|
| Precision, Recall | retrieval quality |
| MRR | rank of the first relevant passage |
| NDCG@10 | graded relevance across the result set |
| Citation accuracy | does the citation resolve to text that says this |
| Attribution accuracy | is the statement correctly assigned to this Mufassir |
| Evidence coverage | fraction of claims with supporting evidence |
| Unsupported claim rate | fraction of claims without it |
| Rule compliance | did retrieval follow the applicable rules |
| Works represented | breadth across Mufassirun for "what do the Tafasir say" |

The last one is specific to this system: a result set that is 100% precise and
drawn entirely from one commentary has failed a comparative question. It is the
metric that would have caught the al-Baghawi monopoly described in
`RETRIEVAL.md`.

## Current test coverage

145 tests.

| Area | Covers |
|---|---|
| Arabic normalisation | display preserves orthography, matching collapses it |
| Reference parsing | numeric, wordy, named, alias forms in three languages |
| Language detection | Arabic/Urdu separation, determinism |
| Classification | signal precedence over keywords |
| Rule engine | tier precedence, provenance reporting |
| Pivot translation | multi-word terms, disclosure of failure |
| Chunking | structural splits, size bounds |
| Schema integrity | `raw_text` immutability, all four rule constraints |
| Retrieval | per-work caps, range overlap, query normalisation |
| Pipeline | three languages end to end, empty-evidence handling |

Every bug found in development became a regression test. Two examples:
`test_sparse_requires_normalised_query` and `test_structural_covers_many_works`.

## Not yet built

A labelled relevance set. It requires scholarly judgement about which passages
answer which questions, which is exactly the kind of work that must not be
automated. Building it is a Phase 2 prerequisite for evaluating dense retrieval.
