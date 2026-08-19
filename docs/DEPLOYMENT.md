# Deployment

## Local development

```bash
docker compose up -d db
cd backend && uv venv && uv pip install -e ".[dev]"
uv run python -m tafahhum.db.migrate
python ../scripts/fetch_corpus.py          # seed a development corpus
uv run pytest
uv run uvicorn tafahhum.api.app:app --reload
```

```bash
cd frontend && npm install && npm run dev   # http://localhost:3000
```

## Port note

The database is published on **5544**, not the PostgreSQL default. A native
PostgreSQL install on the host commonly occupies 5432 and 5433; when it does, it
answers instead of the container and reports `password authentication failed`,
because PostgreSQL returns that error for a non-existent role too. That message
sends you looking for a credentials bug that is not there.

Override with `POSTGRES_PORT` if 5544 is also taken.

## Configuration

Environment variables use the `TAFAHHUM_` prefix and map to `Settings`:

```
TAFAHHUM_POSTGRES_HOST      TAFAHHUM_EMBEDDING_MODEL
TAFAHHUM_POSTGRES_PORT      TAFAHHUM_EVIDENCE_LIMIT
TAFAHHUM_POSTGRES_PASSWORD  TAFAHHUM_PUBLISHED_ONLY
TAFAHHUM_DEFAULT_USER_LANGUAGE
```

`TAFAHHUM_PUBLISHED_ONLY` must remain true on any user-facing deployment. It is a
corpus-maintenance affordance only.

## Before public deployment

Blocking items, in order:

1. **Licensing.** Every edition currently carries `copyright_status = UNKNOWN`.
   Resolve and record each one. See `COPYRIGHT.md`.
2. **Secrets.** `POSTGRES_PASSWORD` has a development default in
   `docker-compose.yml`. Supply a real one.
3. **CORS.** Currently allows localhost:3000 only. Set the real origin.
4. **Rate limiting.** Not implemented. Retrieval is database-bound and a query
   fans out to several index scans.
5. **Migrations.** Run `tafahhum-migrate` as a deploy step; it is idempotent and
   refuses to reapply an edited migration.

## Containerisation

Not yet written. The `vibe-ship` skill generates Dockerfile, compose, CI, and
security hardening in one pass and should be used when the licensing item above
is resolved and deployment is actually imminent.
