# Tafahhum API — multi-stage build
#
# Stage 1 resolves and installs dependencies into a virtualenv; stage 2 copies
# only that virtualenv and the application, so no compiler, package index, or
# build cache reaches the runtime image.

# ---------------------------------------------------------------- builder ----
FROM python:3.13-slim-bookworm AS builder

# uv resolves and installs far faster than pip and honours the lockfile, which
# is what makes the build reproducible.
COPY --from=ghcr.io/astral-sh/uv:0.5.14 /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /build

# Dependency manifests first: this layer is cached until the manifests change,
# so ordinary code edits do not reinstall the dependency tree.
COPY pyproject.toml ./
RUN uv venv /opt/venv \
    && VIRTUAL_ENV=/opt/venv uv pip install --no-cache \
       "fastapi>=0.115" "uvicorn[standard]>=0.34" "psycopg[binary,pool]>=3.2" \
       "pydantic>=2.10" "pydantic-settings>=2.7" "httpx>=0.28" "pymupdf>=1.25"

# ---------------------------------------------------------------- runtime ----
FROM python:3.13-slim-bookworm AS runtime

# curl is needed by the healthcheck and nothing else; the apt cache is removed
# in the same layer so it does not persist in the image.
RUN apt-get update \
    && apt-get install --no-install-recommends -y curl \
    && rm -rf /var/lib/apt/lists/*

# An unprivileged user with no login shell and no home directory to write to.
RUN groupadd --system --gid 10001 tafahhum \
    && useradd --system --uid 10001 --gid tafahhum --no-create-home tafahhum

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000

COPY --from=builder /opt/venv /opt/venv

WORKDIR /app
COPY --chown=tafahhum:tafahhum tafahhum ./tafahhum
COPY --chown=tafahhum:tafahhum migrations ./migrations

USER tafahhum

EXPOSE 8000

# Hits the real health endpoint, which touches the database — so an API that is
# up but cannot reach Postgres is correctly reported unhealthy.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS "http://127.0.0.1:${PORT}/api/v1/health" || exit 1

# Port comes from the environment so the image works behind any proxy or
# platform that assigns one.
CMD ["sh", "-c", "exec uvicorn tafahhum.api.app:app --host 0.0.0.0 --port ${PORT} --proxy-headers --forwarded-allow-ips='*'"]
