# Contributing

## The one rule

Never assert what the sources do not support. If you find yourself writing a
plausible date, a plausible page number, or a plausible methodological principle,
stop and leave the field NULL with a note. A NULL is a fact about the corpus; an
invented value is indistinguishable from a verified one once it is written down.

## Workflow

```
Plan -> Implement -> Test -> Review -> Commit -> Document
```

Every meaningful milestone gets committed. Every bug found becomes a regression
test.

## Running the suite

```bash
cd backend
uv run pytest                    # everything
uv run pytest -m "not db"        # no database needed
uv run ruff check . && uv run mypy tafahhum
```

Database tests skip cleanly when PostgreSQL is unreachable, so a contributor
working on Arabic processing does not need a running database.

## Adding a Tafsir work

Ingestion only. If adding a work requires a schema change, that is a design
defect to report, not to work around.

Record what the source supports and nothing more. If it gives you no death year,
leave `death_year_hijri` NULL — Phase 3 exists to fill those from a
bibliographical source with attestations.

## Adding a rule

Structural rules (`TAFAHHUM_BASELINE`) go in a migration and may not carry a book
attribution; the database enforces this.

Scholarly rules require an ingested bibliographical source, a volume and page
reference, and a named human reviewer. See `SOURCE_POLICY.md` section 6. There is
no shortcut, and the CHECK constraints exist so there cannot be one.

## Migrations

Ordered `.sql` files, applied once, checksummed. Editing an applied migration is
detected and refused. Add a new file instead.

Plain SQL rather than an ORM because the schema leans on features an ORM
abstracts badly: generated `tsvector` columns, GiST range indexes, HNSW vector
indexes, enum types, row triggers, and CHECK constraints that carry policy. The
database, not the application, is where those rules live.

## Style

`ruff` and `mypy --strict`. Line length 100. Comments explain *why*, not *what* —
the code already says what.

Arabic in source files is intentional; the `RUF001-003` ambiguous-unicode rules
are disabled for that reason.
