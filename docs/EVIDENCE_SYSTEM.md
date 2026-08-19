# Evidence System

## The evidence package is a boundary

Everything above it is retrieval. Everything below it is presentation. The
generation layer is a pure function of this object and cannot reach back into the
corpus.

Three structural consequences:

1. **No corpus access from generation.** It cannot retrieve, so it cannot
   silently widen its own evidence.
2. **Citations are pre-minted and opaque.** The generator references evidence by
   `passage_id` handed to it. It has no mechanism to *construct* a citation, so a
   fabricated page number is not expressible.
3. **Post-generation verification.** Claims are extracted and re-matched against
   the package. Unsupported claims are removed or flagged before display.

`EvidencePackage.citable_passage_ids` is the exact set a generated answer may
reference. Anything outside it is a fabrication by definition.

## What assembly does and does not do

Does: group by work, attach Quranic text separately, order chronologically when
the plan asks, compute citation coverage, and state limitations.

Does not: rank interpretations, resolve disagreements, decide which Mufassir is
correct, or merge evidence kinds.

## Limitations are stated, not inferred

Notes are generated from the data, not written by hand:

- no page-level citation in the result set, and why
- the fraction of passages carrying one, when partial
- how many passages remain unverified against a page image
- when query terms could not be carried into Arabic
- when evidence is insufficient

The insufficiency case is a success state:

> Insufficient verified evidence was retrieved from the current corpus.

## Evidence kinds stay distinct

Quranic text, Hadith, Companion report, Tabii report, Mufassir interpretation,
later scholarship, modern analysis, and Tafahhum synthesis each carry an explicit
`evidence_type`. The interface reserves gold for Quranic text and uses it nowhere
else, so revealed text is distinguishable from commentary before a label is read.

## Disagreement

Where retrieved passages support differing interpretations, each position is
presented with its own sources. A synthesis may follow, labelled as Tafahhum
synthesis, but no position is presented as settled unless the sources say so.

Disagreement is never resolved by passage count, similarity score, recency, or
frequency. Retrieval ranking is not scholarly authority.
