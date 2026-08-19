"""Database connectivity."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from functools import lru_cache

import psycopg
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from tafahhum.core.config import get_settings


@lru_cache(maxsize=1)
def get_pool() -> ConnectionPool:
    settings = get_settings()
    return ConnectionPool(
        settings.dsn,
        min_size=settings.pool_min_size,
        max_size=settings.pool_max_size,
        kwargs={"row_factory": dict_row},
        open=True,
    )


@contextmanager
def connection() -> Iterator[psycopg.Connection]:
    with get_pool().connection() as conn:
        yield conn
