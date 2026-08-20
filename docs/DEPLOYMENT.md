# Deployment

## What runs

```text
                    ┌─────────┐
   :80 / :443 ──────│  caddy  │  TLS, security headers, single origin
                    └────┬────┘
              ┌──────────┴──────────┐
              │                     │
        /api/* ▼                    ▼ everything else
          ┌───────┐            ┌───────┐
          │  api  │            │  web  │   Next.js standalone
          └───┬───┘            └───────┘
              │
              ▼
          ┌───────┐
          │  db   │   PostgreSQL 17 + pgvector, no host port
          └───────┘
```

Only Caddy is bound to the host. The API, the web app, and the database sit on
an `internal: true` network and are unreachable from outside the box.

Serving both from one origin is a security decision as much as an operational
one: the browser calls `/api` on the host it loaded the page from, so no CORS
policy has to be relaxed for the app to function.

## Local development

```bash
docker compose up -d db                      # Postgres alone, on :5544
cd backend && uv venv && uv pip install -e ".[dev]"
uv run python -m tafahhum.db.migrate
python ../scripts/fetch_corpus.py            # seed a development corpus
python ../scripts/build_phrases.py           # derive clause structure
uv run pytest
uv run uvicorn tafahhum.api.app:app --reload

cd frontend && npm install && npm run dev    # http://localhost:3000
```

**Port note.** The dev database is published on **5544**, not 5432 or 5433. A
native PostgreSQL install commonly occupies both, and when it does it answers
instead of the container and reports `password authentication failed` — which
PostgreSQL also returns for a role that does not exist. That message sends you
hunting for a credentials bug that is not there.

## Production

```bash
cp .env.example .env        # then fill it in — POSTGRES_PASSWORD has no default
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml exec api python -m tafahhum.db.migrate
```

Compose refuses to start if `POSTGRES_DB`, `POSTGRES_USER`, or
`POSTGRES_PASSWORD` are unset, rather than falling back to a development default
that would ship to a public host.

Set `TAFAHHUM_DOMAIN` to a real hostname and Caddy obtains and renews a
certificate automatically. Left empty it serves plain HTTP on :80 — fine for a
local run, not for anything public.

## Container hardening

| Property | Both images |
| --- | --- |
| User | non-root `tafahhum`, uid 10001 |
| Build | multi-stage; no compiler or package index in the runtime layer |
| Base | pinned (`python:3.13-slim-bookworm`, `node:22-alpine`) |
| Health | `HEALTHCHECK` against a real endpoint |
| Size | api 371 MB, web 299 MB |

The API healthcheck hits `/api/v1/health`, which queries the database — so an
API that is up but cannot reach Postgres is correctly reported unhealthy rather
than passing a check that only proves the process is alive.

`data/scans` is mounted **read-only**. Page images are primary evidence; the API
only reads them, and a writable mount would let a bug in the ingestion path
modify the thing every citation ultimately rests on.

## CI/CD

`.github/workflows/ci-cd.yml`:

1. **backend** — ruff, migrations, and pytest against a real pgvector service,
   because the schema depends on extensions, generated columns, triggers, and
   CHECK constraints that a stub would not reproduce
2. **frontend** — `npm ci` and a production build (which is also the type check)
3. **security** — Trivy filesystem scan for vulnerabilities, secrets, and
   misconfiguration, reported to the Security tab
4. **publish** — builds and pushes both images to GHCR, gated on all three
   passing *and* on the push being to the default branch

`GITHUB_TOKEN` is the only credential needed; there is no registry secret to
manage.

The Trivy step is set to `exit-code: 0` — it reports without blocking. A CVE in
a transitive dependency should be visible without failing an unrelated change.
Tighten it once the backlog is at zero.

## Security review findings

Checked and clean:

- **SQL injection** — every dynamic `WHERE` fragment is a static string with
  `%s` placeholders; all user values go through the parameter list. Verified by
  reading each construction site, not by assuming.
- **Path traversal** — `/api/v1/scans/{id}/image` resolves the stored path and
  refuses anything outside the scan root, so a tampered `image_uri` cannot turn
  the endpoint into an arbitrary file read.
- **Secrets** — none committed; `.env` is gitignored and `.env.example` carries
  placeholders only. The one literal in CI is a throwaway password for an
  ephemeral service container.
- **CORS** — now read from the environment and empty by default. A `*` value is
  dropped rather than honoured, since it would let any site drive a browser
  session against the API.
- **XSS** — no `dangerouslySetInnerHTML`; all Arabic and translated text renders
  as React text nodes.

Outstanding, deliberately not auto-fixed:

- **No rate limiting.** Retrieval is database-bound and one query fans out to
  several index scans. Put a limit in front of `/api/v1/query` and
  `/api/v1/read` before opening this to the public. Adding a rate-limit library
  changes runtime behaviour, so it is flagged rather than slipped in.
- **Licensing is unresolved.** Every edition carries
  `copyright_status = UNKNOWN`. This is a blocking item for a public deployment,
  not a formality. See `COPYRIGHT.md`.
- **Translation costs money if a key is set.** `ANTHROPIC_API_KEY` is optional;
  without it translation returns an explicit 503 and the Arabic is unaffected.
  With it, a public endpoint that triggers model calls needs the rate limit
  above first.
- **No backups configured.** `pgdata` is a named volume. Add
  `pg_dump` to a schedule before the corpus represents real review effort.

## Scaling notes

The app containers are stateless — state is in Postgres, and the only disk read
is the read-only scan mount — so `web` and `api` can be replicated behind Caddy
without further change. Worth doing only when measurements call for it:

- connection pooling (PgBouncer) once concurrent queries exceed the pool
- a CDN in front of `.next/static`
- moving translation to a queue, since a local model takes minutes per passage
