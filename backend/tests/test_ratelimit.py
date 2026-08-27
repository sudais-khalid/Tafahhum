"""The rate limiter's behaviour, pinned.

These test the arithmetic rather than the HTTP layer: a limiter that silently
stops limiting is indistinguishable from a working one until the day it
matters, so the refusal, the refill and the tiering are each asserted.
"""

from __future__ import annotations

from tafahhum.api.ratelimit import TIERS, RateLimiter, tier_for


class TestTiering:
    def test_model_work_is_its_own_tier(self):
        """Translation and summary start model work and are metered hardest."""
        assert tier_for("/api/v1/passages/abc/translate") == "model"
        assert tier_for("/api/v1/read/2/255/summary") == "model"

    def test_reading_is_the_read_tier(self):
        assert tier_for("/api/v1/query") == "read"
        assert tier_for("/api/v1/read/2/255") == "read"
        assert tier_for("/api/v1/ayah/2/255") == "read"

    def test_health_is_never_limited(self):
        """Metering the healthcheck turns a busy minute into a restart loop."""
        assert tier_for("/api/v1/health") is None

    def test_model_tier_is_the_scarcest(self):
        model, _ = TIERS["model"]
        read, _ = TIERS["read"]
        default, _ = TIERS["default"]
        assert model < read < default


class TestBucket:
    def test_burst_is_allowed_then_refused(self):
        limiter = RateLimiter(tiers={"model": (6, 3)})
        allowed = sum(1 for _ in range(9) if limiter.check("a", "model")[0])
        assert allowed == 9, "the full ceiling should be spendable as a burst"

        ok, retry = limiter.check("a", "model")
        assert not ok
        assert retry >= 1, "a refusal must say when to come back"

    def test_clients_do_not_share_an_allowance(self):
        limiter = RateLimiter(tiers={"model": (6, 3)})
        for _ in range(9):
            limiter.check("a", "model")
        assert limiter.check("a", "model")[0] is False
        assert limiter.check("b", "model")[0] is True, "one caller exhausted another"

    def test_tiers_do_not_share_an_allowance(self):
        limiter = RateLimiter(tiers={"model": (6, 3), "read": (90, 30)})
        for _ in range(9):
            limiter.check("a", "model")
        assert limiter.check("a", "model")[0] is False
        assert limiter.check("a", "read")[0] is True

    def test_tokens_refill_over_time(self):
        limiter = RateLimiter(tiers={"model": (60, 0)})
        for _ in range(60):
            limiter.check("a", "model")
        assert limiter.check("a", "model")[0] is False

        # One token a second at 60/minute. Rewinding the bucket's clock is the
        # same arithmetic as waiting, without the wait.
        bucket = limiter._buckets[("a", "model")]
        bucket.updated -= 2.0
        assert limiter.check("a", "model")[0] is True

    def test_idle_buckets_are_swept(self):
        """Otherwise the map grows once per client forever."""
        limiter = RateLimiter(tiers={"read": (90, 30)})
        limiter.check("old", "read")
        limiter._buckets[("old", "read")].updated -= 700
        limiter._last_sweep -= 120

        limiter.check("new", "read")
        assert ("old", "read") not in limiter._buckets
        assert ("new", "read") in limiter._buckets
