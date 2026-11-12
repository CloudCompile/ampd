"""Unit tests for Apple 429/backoff handling and the cache-only-200 rule.

All hermetic — _raw_api_now (the eval boundary) is mocked; nothing touches
Chrome. The known quirks under test:
  * GETs retry on 429 honoring Retry-After (bounded); mutations never retry
  * a wrong-key favorites DELETE returns 204 and does NOTHING — so mutation
    retries would silently mask state; they must not happen
  * a cached 404/429 would serve a not-yet-applied snapshot across Apple's
    async mutation window — only 200s are cacheable
"""
import os
import sys
import time
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tonearm import musickit as mk
from tonearm.cache import ReadCache


def res429(retry_after=None):
    return {"status": 429, "retryAfter": retry_after, "body": "rate limited"}


def res200(body='{"ok": true}'):
    return {"status": 200, "retryAfter": None, "body": body}


class TestBackoff(unittest.TestCase):
    def setUp(self):
        # fresh cache per test — the real singleton would leak a cached 200
        # across tests sharing a path (exactly the staleness it guards against)
        self._rc = mock.patch.object(mk, "read_cache", ReadCache())
        self._rc.start()
        self.addCleanup(self._rc.stop)
        self.sleeps = []
        self._sleep = mock.patch.object(mk.time, "sleep",
                                        side_effect=self.sleeps.append)
        self._sleep.start()
        self.addCleanup(self._sleep.stop)

    def test_429_then_200_recovers(self):
        with mock.patch.object(mk, "_raw_api_now",
                               side_effect=[res429("1"), res200()]) as raw:
            out = mk.raw_api("/v1/me/library/songs?limit=10")
        self.assertEqual(out["status"], 200)
        self.assertEqual(raw.call_count, 2)
        self.assertEqual(self.sleeps, [1.0], "Retry-After=1 -> 1s sleep")

    def test_bounded_tries_then_returns_last_429(self):
        with mock.patch.object(mk, "_raw_api_now",
                               return_value=res429()) as raw:
            out = mk.raw_api("/v1/me/library/songs?limit=10")
        self.assertEqual(out["status"], 429, "exhausted backoff returns the 429")
        self.assertEqual(raw.call_count, mk._BACKOFF_TRIES)

    def test_retry_after_capped(self):
        with mock.patch.object(mk, "_raw_api_now",
                               side_effect=[res429("120"), res200()]):
            mk.raw_api("/v1/me/library/songs?limit=10")
        self.assertLessEqual(self.sleeps[0], mk._BACKOFF_CAP_S,
                             "a huge Retry-After must not stall the server")

    def test_missing_or_garbage_retry_after_uses_escalating_jitter(self):
        with mock.patch.object(mk, "_raw_api_now",
                               side_effect=[res429(), res429("soon"), res200()]):
            mk.raw_api("/v1/me/library/songs?limit=10")
        self.assertEqual(self.sleeps, [0.5, 1.0])

    def test_mutations_never_retry(self):
        """The wrong-key-DELETE-204 quirk means blind mutation retries would
        mask real state. One attempt, always."""
        with mock.patch.object(mk, "_raw_api_now",
                               return_value=res429()) as raw:
            out = mk.raw_api("/v1/me/favorites", method="DELETE")
        self.assertEqual(out["status"], 429)
        self.assertEqual(raw.call_count, 1)
        self.assertEqual(self.sleeps, [])

    def test_200_never_sleeps(self):
        with mock.patch.object(mk, "_raw_api_now", return_value=res200()) as raw:
            mk.raw_api("/v1/me/library/songs?limit=10")
        self.assertEqual(raw.call_count, 1)
        self.assertEqual(self.sleeps, [])


class TestCacheOnly200(unittest.TestCase):
    def setUp(self):
        self.rc = ReadCache()
        self._orig = mk.read_cache
        mk.read_cache = self.rc
        self.addCleanup(setattr, mk, "read_cache", self._orig)

    def test_200_cached(self):
        with mock.patch.object(mk, "_raw_api_now", return_value=res200()) as raw:
            mk.raw_api("/k")
            mk.raw_api("/k")
        self.assertEqual(raw.call_count, 1, "200 served from cache")

    def test_404_never_cached(self):
        """A cached 404 would hide a mutation that lands a beat later
        (Apple applies async) — negatives must always re-fetch."""
        notfound = {"status": 404, "retryAfter": None, "body": "nope"}
        with mock.patch.object(mk, "_raw_api_now", return_value=notfound) as raw:
            mk.raw_api("/v1/me/ratings/songs/123")
            mk.raw_api("/v1/me/ratings/songs/123")
        self.assertEqual(raw.call_count, 2, "404 must not be cached")

    def test_429_never_cached(self):
        limited = res429()
        with mock.patch.object(mk, "_raw_api_now", return_value=limited) as raw:
            mk.raw_api("/k")
            mk.raw_api("/k")
        # each raw_api call burns the full 3-attempt backoff against a
        # persistent 429 — 2 calls x 3 tries; the point is neither call was
        # served from cache
        self.assertEqual(raw.call_count, 6)

    def test_coalesce_cache_when_predicate(self):
        rc = ReadCache()
        seen = []
        rc.coalesce("/k", lambda: seen.append(1) or {"status": 404},
                    cache_when=lambda v: v.get("status") == 200)
        rc.coalesce("/k", lambda: seen.append(2) or {"status": 404},
                    cache_when=lambda v: v.get("status") == 200)
        self.assertEqual(seen, [1, 2], "filtered results must not store")


if __name__ == "__main__":
    unittest.main(verbosity=2)
