# Retrieval

## Three strategies

| Strategy | Mechanism | Answers |
|---|---|---|
| **structural** | `passage_ayah` range overlap | "commentary on 2:255", exactly |
| **sparse** | PostgreSQL `tsvector`, Arabic config | exact phrases, names, technical terms |
| **dense** | pgvector cosine, HNSW | concepts worded differently from the text |

Each runs independently. Dense returns nothing when the corpus is un-embedded and
the system degrades to structural plus sparse rather than failing, because a
partially ingested corpus is a normal state.

## Why hybrid is not optional

A researcher searching an exact Arabic phrase needs lexical matching; vector
search returns "similar" passages that do not contain it. A user asking what
scholars say about divine forgiveness needs semantic matching; the relevant
passage may use المغفرة, العفو, or التوبة and never the queried word. Neither
strategy subsumes the other.

## Fusion: reciprocal rank, not score

A `ts_rank` value and a cosine distance are not comparable. They have different
scales, different distributions, and no principled conversion. Normalising them
onto a shared range invents a relationship that does not exist.

RRF fuses on rank:

```
score(p) = sum over strategies s of  weight_s / (k + rank_s(p))
```

`k = 60`, from the original RRF paper, untuned, because it is stable across very
different rankers. Structural retrieval carries weight 1.5 because it is exact
where the others are approximate.

## Per-work partitioning

Commentary length varies enormously. Across the seeded ayahs al-Razi produces 501
passages where al-Jalalayn produces 21. An undifferentiated `ORDER BY` therefore
fills the result set with whichever Mufassir wrote at greatest length, and length
silently acts as relevance.

This was observed, not anticipated: the first working build returned eight
results, all from al-Baghawi.

The fix is structural. `search_structural` ranks within each work using a window
function before combining:

```sql
ROW_NUMBER() OVER (
  PARTITION BY w.slug
  ORDER BY pa.surah_number, pa.ayah_start, p.sequence_index
)
```

Ordering output by `work_rank` first interleaves the works, so a passage's fused
rank reflects its standing inside its own commentary. A second `diversify_by_work`
pass caps passages per work after fusion, since fusion alone does not guarantee
breadth.

For a question of the form "what do the Tafasir say", breadth across Mufassirun
*is* the answer.

## Query normalisation

The FTS index is built over `normalized_text`. A query must pass through the
identical normalisation or the two never meet: the index stores معني, the user
types معنى, and the search silently returns nothing.

This bug existed and is now covered by `test_sparse_requires_normalised_query`.

## Ranking is not authority

Retrieval order is a relevance estimate. It is never used to decide which
Mufassir is correct, which position is the majority, or which interpretation to
prefer. Rule `evidence.rank_is_not_authority` states this, and disagreement
handling never counts passages.

## Configuration

| Setting | Default | Meaning |
|---|---|---|
| `sparse_candidate_limit` | 100 | per-strategy candidate pool |
| `dense_candidate_limit` | 100 | |
| `rerank_limit` | 40 | passed to the reranker |
| `evidence_limit` | 12 | reaches the user |
| `rrf_k` | 60 | fusion constant |
| `embedding_dimensions` | 1024 | BGE-M3; changing it needs a migration |
