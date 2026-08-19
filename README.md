<div align="center">

# Tafahhum · تَفَهُّم

**Explore the legacy of Quranic interpretation.**

A research platform for the historical tradition of Quranic Tafsir —
discovery, evidence, context, provenance, and comparison.

</div>

---

## What this is

Tafahhum is a scholarly research and retrieval platform for the historical Tafsir
tradition. It indexes Tafasir, Mufassirun, editions, and page-level provenance so a
researcher can move from a question all the way back to the original scanned page:

```
Answer → Interpretation → Mufassir → Tafsir → Edition → Volume → Page → Scan
```

It is **not** a Quran chatbot. It does not author Tafsir. Every scholarly claim it
surfaces is traceable to an indexed passage in a specific edition, or it is not
surfaced at all.

## Core principle

```
SOURCE → STRUCTURE → RETRIEVE → VERIFY → SYNTHESIZE → CITE
```

Never reversed. The system does not generate an answer and then look for evidence.

## Languages

Arabic is the **pivot language** of the system: the corpus is Arabic, retrieval runs in
Arabic, and evidence is assembled in Arabic. Users may work in **Arabic, English, or
Urdu** — queries are normalised into the pivot, and presentation is rendered back into
the user's language.

Source quotations are **never silently translated**. An Arabic passage is always shown
in Arabic; any translation is labelled as a translation and carries its own provenance.

## Status

Early implementation. See [docs/ROADMAP.md](docs/ROADMAP.md) for phases and
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the system design.

> **Corpus note:** this repository contains **no Tafsir text**. The corpus is built by
> ingesting sources you supply, under the licence terms of the specific edition used.
> See [docs/SOURCE_POLICY.md](docs/SOURCE_POLICY.md) and [docs/COPYRIGHT.md](docs/COPYRIGHT.md).

## Quick start

```bash
docker compose up -d db                    # PostgreSQL 17 + pgvector, port 5544
cd backend && uv venv && uv pip install -e ".[dev]"
uv run python -m tafahhum.db.migrate       # applies migrations/*.sql in order
python ../scripts/fetch_corpus.py          # seed a development corpus
uv run pytest
uv run uvicorn tafahhum.api.app:app --reload

cd frontend && npm install && npm run dev  # http://localhost:3000
```

## Documentation

| Document | Contents |
|---|---|
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | System design and layer boundaries |
| [DATA_MODEL.md](docs/DATA_MODEL.md) | Entities, relationships, schema rationale |
| [CORPUS_PIPELINE.md](docs/CORPUS_PIPELINE.md) | Acquisition → scan → OCR → verify → index |
| [ARABIC_PROCESSING.md](docs/ARABIC_PROCESSING.md) | Normalisation, diacritics, orthography |
| [LANGUAGE_PIPELINE.md](docs/LANGUAGE_PIPELINE.md) | Arabic pivot, ar/en/ur user languages |
| [RETRIEVAL.md](docs/RETRIEVAL.md) | Hybrid sparse + dense + metadata + rerank |
| [RULE_ENGINE.md](docs/RULE_ENGINE.md) | Scholarly rules and their provenance |
| [EVIDENCE_SYSTEM.md](docs/EVIDENCE_SYSTEM.md) | Evidence assembly and citation verification |
| [EVALUATION.md](docs/EVALUATION.md) | Benchmarks and metrics |
| [SOURCE_POLICY.md](docs/SOURCE_POLICY.md) | What may enter the corpus, and how |
| [COPYRIGHT.md](docs/COPYRIGHT.md) | Edition-level licensing |
| [DESIGN_SYSTEM.md](docs/DESIGN_SYSTEM.md) | Visual language, Arabic typography |
| [ROADMAP.md](docs/ROADMAP.md) | Phases |
| [CONTRIBUTING.md](docs/CONTRIBUTING.md) | Development workflow |
| [DEPLOYMENT.md](docs/DEPLOYMENT.md) | Running in production |

## Author

**Sudais Khalid** — [sudaiskhalid.com](https://sudaiskhalid.com)
