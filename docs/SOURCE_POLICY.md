# Source Policy

What may enter the Tafahhum corpus, in what state, and under what claims.

## 1. The prohibition

Tafahhum must never:

- fabricate a citation, quotation, page number, volume, or edition
- invent a Mufassir, a Tafsir work, or historical metadata
- attribute a statement to a scholar without an indexed passage supporting it
- manufacture scholarly consensus
- suppress a recorded disagreement
- record a source as verified when it has not been verified by a human

When evidence is insufficient the system says so. That output is correct behaviour.

## 2. No text ships with this repository

This repository contains **no Tafsir text and no Quranic text**. The corpus is
constructed by ingestion from sources the operator supplies and is legally entitled to
use. Nothing is bundled, vendored, or seeded with scholarly content.

Test fixtures use synthetic Arabic strings that are **not** Tafsir and are marked
`verification_status = 'FIXTURE'`. Fixture-state rows are excluded from every
user-facing query path by a database-level predicate, not by application convention.

## 3. Verification states

A work moves through `corpus_status` (see `DATA_MODEL.md`):

```
DISCOVERED → ACQUIRED → SCANNED → OCR_COMPLETE → NORMALIZED
  → AYAH_ALIGNED → METADATA_COMPLETE → HUMAN_REVIEW → VERIFIED → INDEXED → PUBLISHED
```

Only `PUBLISHED` works are visible to end users by default. `VERIFIED` means a human
reviewer approved the text against the page image — not that a heuristic passed.

## 4. Reliability is multi-dimensional

There is no single "accuracy score". These are tracked separately because they are
different claims about different things, and averaging them destroys the information:

| Dimension | Question it answers |
|---|---|
| `source_authenticity` | Is this work genuinely by this author? |
| `edition_quality` | Is this a critical edition, or an uncredited reprint? |
| `ocr_confidence` | How reliably was the glyph stream recovered? |
| `text_verification` | Did a human approve this text against the scan? |
| `metadata_confidence` | Are the dates, places, and attributions sound? |
| `citation_precision` | Does the volume/page resolve to the exact passage? |
| `historical_attribution_confidence` | Is the dating of the work itself secure? |

A passage may have excellent OCR confidence and poor attribution confidence. That is a
meaningful, reportable state.

## 5. Editions are not interchangeable

A Tafsir work and an edition of that work are separate entities. Two editions of
al-Ṭabarī differ in volume count, pagination, editorial apparatus, and legal status.
A citation is meaningless without the edition it refers to. Passages are therefore
attached to an `edition_id`, never to a work alone.

## 6. Bibliographical foundation — current state

The bibliographical layer (the catalogue of Mufassirūn and their works) is to be built
from established biographical and bibliographical sources in the *ṭabaqāt al-mufassirīn*
genre.

### ⚠ Open scholarly verification item: نيل السائرين في طبقات المفسرين

The project designates **Nayl al-Sāʾirīn fī Ṭabaqāt al-Mufassirīn** as a primary
bibliographical source and intends the retrieval methodology to be grounded in it.

**The text of this work is not present in this repository, and no part of the
implementation asserts any claim, principle, ordering, or classification on its
authority.** The rule engine ships with **zero** rules attributed to it.

This is deliberate and follows the project's own directive: *never invent a rule and
attribute it to the book.* Producing plausible-sounding methodological rules and
labelling them as derived from a book whose text has not been read would be exactly the
fabrication this policy prohibits — and it would be undetectable to a user, because the
rules would carry a citation that looks correct.

**To ground the methodology in this work, the required path is:**

```
Acquire the text (edition identified, licence cleared)
        ↓
Ingest as a first-class corpus work (it is a source about sources)
        ↓
Scholarly reading of the relevant passages
        ↓
Draft candidate principles, each anchored to volume + page
        ↓
Human scholarly review and approval
        ↓
Insert as rules with source_reference populated and
        verification_status = 'VERIFIED'
```

Until that path is walked, the engine operates on **baseline structural rules only**.
Those are labelled `source_book = 'TAFAHHUM_BASELINE'` and
`verification_status = 'UNVERIFIED'`. They govern mechanical retrieval behaviour
(e.g. "a comparative query retrieves each named Mufassir independently") and make **no
scholarly claim whatsoever**. They are not attributed to any book, and the schema
forbids them from being.

The database enforces this: a rule row claiming a scholarly `source_book` **must** carry
a non-null `source_reference` and cannot be set `VERIFIED` without a `verified_by`
reviewer identity. See `migrations/002_rules.sql`.

## 7. Provenance of rules

Every rule must answer: *why did Tafahhum retrieve this source?*

```
Rule → Scholarly Source → Book → Edition → Volume → Page
```

There are no hidden rules. `GET /api/v1/rules` exposes the full active rule set with
provenance for inspection.

## 8. Type distinction is mandatory

The following are never silently merged in output:

```
Quranic Text · Hadith · Companion Report · Tābiʿī Report
· Mufassir Interpretation · Later Scholarly Interpretation
· Modern Academic Analysis · Tafahhum Synthesis
```

Each carries an explicit `evidence_type`. The user must always know what kind of
evidence they are reading. A synthesis produced by Tafahhum is labelled as such and is
never presented as a quotation.

## 9. Translation is not source text

A translation of an Arabic passage into English or Urdu is a derived artefact. It is
stored separately, labelled, attributed to its translator (human or machine), and never
substituted for the original in a citation. See `LANGUAGE_PIPELINE.md`.
