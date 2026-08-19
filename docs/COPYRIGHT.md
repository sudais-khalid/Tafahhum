# Copyright and Licensing

## The rule that catches people out

An old text does not make a modern edition public domain. A critical edition
carries editorial work — vocalisation, apparatus, indices, pagination — that is
protected independently of the historical text it presents.

`copyright_status` therefore includes `PUBLIC_DOMAIN_TEXT_EDITION_RESTRICTED` as
a distinct state, because it is the common case for classical Tafsir.

## Tracked per edition

```
copyright_status         redistribution_allowed
license                  commercial_use_allowed
source_license           license_note
digital_source_url
```

Licensing attaches to the edition, never to the work, because the work and its
printings have different legal status.

## This repository ships no text

No Tafsir text and no Quranic text is committed. `data/` holds cache and seed
artefacts and is gitignored for scans, OCR, and editions. The corpus is built by
ingesting sources the operator supplies and is entitled to use.

## Current corpus status

The development corpus seeded by `scripts/fetch_corpus.py` is marked
`copyright_status = UNKNOWN`, and every edition carries a licence note recording
that the underlying print edition is unidentified.

**UNKNOWN means unresolved, not permissive.** Before any redistribution or
public deployment, each edition's status must be established and recorded. This
is a blocking item for public launch, not a formality.

## Quranic text

Seeded from Tanzil via alquran.cloud, recorded as `PUBLIC_DOMAIN` with the source
URL and licence field populated. The riwayah is recorded explicitly
(Hafs an Asim, Uthmani script), because a Quranic text is a sourced artefact like
any other and has no default.
