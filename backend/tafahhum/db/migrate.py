"""Migration runner.

Plain ordered .sql files rather than an ORM migration tool. The schema leans on
PostgreSQL features an ORM abstracts badly — generated tsvector columns, GiST
range indexes, HNSW vector indexes, enum types, row triggers, and CHECK
constraints that carry policy. Writing those as SQL keeps them readable and keeps
the database, not the application, as the place the rules live.

Each file is applied once, inside a transaction, and recorded with a checksum so
that editing an already-applied migration is detected rather than silently ignored.
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import psycopg

from tafahhum.core.config import get_settings

MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "migrations"

BOOTSTRAP = """
CREATE TABLE IF NOT EXISTS schema_migration (
    filename    text PRIMARY KEY,
    applied_at  timestamptz NOT NULL DEFAULT now(),
    checksum    text NOT NULL
);
"""


def checksum(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def discover() -> list[Path]:
    return sorted(MIGRATIONS_DIR.glob("*.sql"))


def apply_all(dsn: str, *, verbose: bool = True) -> int:
    """Apply every pending migration. Returns the number applied."""
    files = discover()
    if not files:
        raise RuntimeError(f"no migrations found in {MIGRATIONS_DIR}")

    applied = 0
    with psycopg.connect(dsn, autocommit=False) as conn:
        with conn.cursor() as cur:
            cur.execute(BOOTSTRAP)
            conn.commit()

            cur.execute("SELECT filename, checksum FROM schema_migration")
            seen = dict(cur.fetchall())

        for path in files:
            sql = path.read_text(encoding="utf-8")
            digest = checksum(sql)

            if path.name in seen:
                if seen[path.name] != digest:
                    raise RuntimeError(
                        f"{path.name} was already applied but its contents changed "
                        f"(recorded {seen[path.name]}, now {digest}). "
                        f"Add a new migration instead of editing an applied one."
                    )
                if verbose:
                    print(f"  = {path.name}")
                continue

            with conn.cursor() as cur:
                try:
                    cur.execute(sql)  # type: ignore[arg-type]
                    cur.execute(
                        "INSERT INTO schema_migration (filename, checksum) VALUES (%s, %s)",
                        (path.name, digest),
                    )
                    conn.commit()
                except Exception:
                    conn.rollback()
                    print(f"  x {path.name} FAILED", file=sys.stderr)
                    raise
            applied += 1
            if verbose:
                print(f"  + {path.name}")

    return applied


def main() -> int:
    settings = get_settings()
    print(
        f"applying migrations to {settings.postgres_db}"
        f"@{settings.postgres_host}:{settings.postgres_port}"
    )
    count = apply_all(settings.dsn)
    print(f"done: {count} migration(s) applied")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
