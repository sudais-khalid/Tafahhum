"""Per-client rate limiting.

Without this, one caller can hold the whole service down, and not by malice:
the summary endpoint starts a model job that runs for minutes, and the
translate endpoint loads a 600MB model and decodes on CPU. A handful of
concurrent requests to either is enough to exhaust a small host.

So the limits are not uniform. Reading is cheap and generous; anything that
starts model work is scarce and metered accordingly.

## Why a token bucket, and why in process

A fixed window lets a caller spend the whole allowance in the last second of
one window and the whole of the next in the first second, which is twice the
intended rate at the moment it matters least. A token bucket refills smoothly
and permits a small burst on top, which is what a browser opening a page of
passages actually looks like.

State lives in this process. That is the correct trade for a single-instance
deployment and it is honest about its limit: run more than one replica and each
gets its own allowance, so the effective limit multiplies by the replica count.
Putting the counters in Postgres would make a rate limiter that costs a
database round trip per request, which defeats the purpose; the moment there is
more than one replica, this should move to Redis rather than grow here.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field

from fastapi import Request
from fastapi.responses import JSONResponse

#: Requests per minute and the burst allowed above it, per client, per tier.
#:
#: Model work is the scarce resource: a summary occupies the generator for
#: minutes and a translation loads and runs an NMT model, so those get single
#: digits per minute. Reading is a database query and can be generous.
TIERS: dict[str, tuple[float, int]] = {
    "model": (6, 3),
    "read": (90, 30),
    "default": (180, 60),
}

#: Path fragments that identify the expensive endpoints. Matched as substrings
#: because the paths carry ids.
_MODEL_PATHS = ("/translate", "/summary")
_READ_PATHS = ("/query", "/read/", "/ayah/", "/passages", "/parse")

#: Never metered: the healthcheck is what the orchestrator uses to decide
#: whether this container is alive, and rate limiting it turns a busy minute
#: into a restart loop.
_EXEMPT = ("/health",)


def tier_for(path: str) -> str | None:
    """Which allowance a path draws on, or None when it is exempt."""
    if any(p in path for p in _EXEMPT):
        return None
    if any(p in path for p in _MODEL_PATHS):
        return "model"
    if any(p in path for p in _READ_PATHS):
        return "read"
    return "default"


@dataclass
class _Bucket:
    tokens: float
    updated: float


@dataclass
class RateLimiter:
    """Token buckets keyed by client and tier."""

    tiers: dict[str, tuple[float, int]] = field(default_factory=lambda: dict(TIERS))
    _buckets: dict[tuple[str, str], _Bucket] = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock)
    _last_sweep: float = field(default_factory=time.monotonic)

    def check(self, client: str, tier: str) -> tuple[bool, int]:
        """Spend a token. Returns (allowed, seconds to wait when refused)."""
        per_minute, burst = self.tiers[tier]
        rate = per_minute / 60.0
        ceiling = per_minute + burst
        now = time.monotonic()
        key = (client, tier)

        with self._lock:
            self._sweep(now)
            bucket = self._buckets.get(key)
            if bucket is None:
                bucket = _Bucket(tokens=ceiling, updated=now)
                self._buckets[key] = bucket

            # Refill for the time that passed, never above the ceiling.
            bucket.tokens = min(ceiling, bucket.tokens + (now - bucket.updated) * rate)
            bucket.updated = now

            if bucket.tokens >= 1.0:
                bucket.tokens -= 1.0
                return True, 0

            # How long until one whole token exists again.
            wait = (1.0 - bucket.tokens) / rate if rate > 0 else 60
            return False, max(1, int(wait) + 1)

    def _sweep(self, now: float) -> None:
        """Drop buckets that have been full and idle.

        Without this the dictionary grows once per distinct client forever,
        which is a slow memory leak that only shows up under the traffic it was
        built to survive. Called under the lock, at most once a minute.
        """
        if now - self._last_sweep < 60:
            return
        self._last_sweep = now
        stale = [k for k, b in self._buckets.items() if now - b.updated > 600]
        for k in stale:
            del self._buckets[k]


_limiter = RateLimiter()


def client_key(request: Request) -> str:
    """Identify the caller.

    Behind a reverse proxy the socket address is the proxy, so the first hop in
    X-Forwarded-For is used when present. That header is client-controlled and
    trivially spoofed, so it is only a fair-use key, never an authorisation
    decision. Anything that gated access on identity would need real
    authentication instead.
    """
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        first = forwarded.split(",")[0].strip()
        if first:
            return first
    return request.client.host if request.client else "unknown"


async def rate_limit_middleware(request: Request, call_next):
    tier = tier_for(request.url.path)
    if tier is None:
        return await call_next(request)

    allowed, retry_after = _limiter.check(client_key(request), tier)
    if not allowed:
        return JSONResponse(
            status_code=429,
            headers={"Retry-After": str(retry_after)},
            content={
                "detail": (
                    "Too many requests. This instance limits how often the "
                    "commentaries can be searched and translated so that one "
                    "caller cannot exhaust it for everyone."
                ),
                "retry_after_seconds": retry_after,
            },
        )
    return await call_next(request)
