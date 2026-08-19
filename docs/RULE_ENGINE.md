# Rule Engine

## Rules are data

Rules live in `scholarly_rule`, load per query, and merge into a `RetrievalPlan`.
The set that fired is recorded in `query_run_rule`, so "why did Tafahhum retrieve
this source?" has an answer that terminates in a citation.

`GET /api/v1/rules` returns the full active set. There are no hidden rules.

## Seven tiers, strictly ordered

```
1  SYSTEM_INTEGRITY       <- cannot be relaxed by anything below
2  SOURCE_PROVENANCE
3  SCHOLARLY_METHOD       <- the only tier that may cite a book
4  QUERY_STRATEGY
5  EVIDENCE_QUALITY
6  RESPONSE_STRUCTURE
7  LANGUAGE_GENERATION
```

Rules arrive in tier order. The first rule to set an effect key locks it, so a
lower tier cannot override a higher one. Exclusions are the exception: they
accumulate, because excluding a source is always a tightening.

The direction matters. Systems like this fail by letting a presentation
preference quietly loosen a provenance requirement.

## Provenance enforced by the database

Four CHECK constraints in `005_rules.sql` make an unsourced scholarly rule
*unrepresentable*:

1. A rule attributed to a book must carry a `source_reference`.
2. It must link a `biblio_source` record.
3. Nothing reaches `VERIFIED` without `verified_by` and `verified_at`.
4. Only `SCHOLARLY_METHOD` may carry a book attribution, and a `SCHOLARLY_METHOD`
   rule may never be baseline.

Constraint 4 stops a structural rule from acquiring scholarly authority by having
its `source_book` edited. All four are tested in
`test_integration.py::TestSchemaIntegrity`.

## Current state: zero scholarly rules

The engine ships with **16 baseline rules and 0 attributed to any book.**

Baseline rules are labelled `TAFAHHUM_BASELINE`, govern mechanical retrieval
behaviour, and make no scholarly claim: retrieve each work independently, run
both sparse and dense, report insufficient evidence rather than filling the gap,
never treat rank as authority.

Zero scholarly rules is the honest state until a bibliographical source has been
ingested, read, drafted into candidate principles, and reviewed by a qualified
human. Writing plausible methodological rules and labelling them as derived from
an unread book would be fabrication a user could not detect, because the citation
would look correct.

`test_no_rule_claims_a_scholarly_source_yet` guards this. When the first verified
scholarly rule lands, that test is updated deliberately.

## Adding a scholarly rule

```
Acquire text -> ingest as biblio_source -> scholarly reading
  -> draft principle anchored to volume and page
  -> human review -> INSERT with source_reference and verified_by
```
