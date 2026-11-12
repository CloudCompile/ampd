"""Unit tests for the read cache + coalescer (no Chrome, no network).

Run:  python3 -m unittest discover -s tests
CI runs this — everything here is hermetic.
"""
import os
import sys
import threading
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ampd.cache import ReadCache


def fresh_cache(**env):
    """A ReadCache as if the given env had been set at import."""
    saved = {k: os.environ.pop(k, None) for k in
             ("AMPD_CACHE", "AMPD_CACHE_TTL")}
    try:
        os.environ.update({k: v for k, v in env.items()})
        return ReadCache()
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


class TestTTL(unittest.TestCase):
    def test_hit_and_expiry(self):
        rc = fresh_cache(AMPD_CACHE_TTL="0.05")
        rc.put("/k", {"v": 1})
        self.assertEqual(rc.get("/k"), {"v": 1})
        time.sleep(0.07)
        self.assertIsNone(rc.get("/k"))

    def test_family_ttls(self):
        rc = fresh_cache(AMPD_CACHE_TTL="10")
        self.assertEqual(rc.ttl_for("/v1/catalog/us/songs/1"), 100.0)
        self.assertEqual(rc.ttl_for("/v1/me/favorites?ids=1"), 10.0)
        self.assertEqual(rc.ttl_for("/v1/me/library/songs?limit=100"), 10.0)
        rc = fresh_cache(AMPD_CACHE_TTL="30")
        self.assertEqual(rc.ttl_for("/v1/me/ratings/songs/1"), 10.0,
                         "favorites/ratings cap short even with a big base TTL")

    def test_disabled(self):
        rc = fresh_cache(AMPD_CACHE="0")
        self.assertFalse(rc.enabled)
        calls = []
        rc.coalesce("/k", lambda: calls.append(1) or "x")
        rc.coalesce("/k", lambda: calls.append(2) or "y")
        self.assertEqual(len(calls), 2, "disabled cache must never serve")

    def test_eviction_bounded(self):
        rc = fresh_cache(AMPD_CACHE_TTL="60")
        for i in range(600):
            rc.put(f"/k{i}", i)
        self.assertLessEqual(len(rc._entries), 500)


class TestCoalescing(unittest.TestCase):
    def test_in_flight_calls_collapse(self):
        rc = fresh_cache(AMPD_CACHE_TTL="60")
        n = [0]
        barrier = threading.Barrier(6)

        def fetch():
            n[0] += 1
            time.sleep(0.4)          # leader works; followers pile up
            return {"ok": True}

        results, errs = [], []
        def worker():
            barrier.wait()
            try:
                results.append(rc.coalesce("/same/path", fetch))
            except Exception as e:
                errs.append(e)

        threads = [threading.Thread(target=worker) for _ in range(6)]
        for t in threads: t.start()
        for t in threads: t.join(5)
        self.assertFalse(errs)
        self.assertEqual(n[0], 1, "identical in-flight GETs must be 1 fetch")
        self.assertEqual(results, [{"ok": True}] * 6)

    def test_leader_failure_lets_follower_retry(self):
        rc = fresh_cache(AMPD_CACHE_TTL="60")
        state = {"fail": True}
        def fetch():
            if state["fail"]:
                state["fail"] = False
                raise RuntimeError("leader boom")
            return "recovered"
        out = []
        def leader():
            try:
                rc.coalesce("/k", fetch)
            except RuntimeError:
                pass            # expected — the point of the test
        t = threading.Thread(target=leader)
        t.start()
        time.sleep(0.1)              # leader is failing right now
        self.assertEqual(rc.coalesce("/k", fetch), "recovered")
        t.join(5)

    def test_fresh_bypasses(self):
        rc = fresh_cache(AMPD_CACHE_TTL="60")
        rc.put("/k", "stale")
        seen = []
        out = rc.coalesce("/k", lambda: seen.append(1) or "fresh", fresh=True)
        self.assertEqual(out, "fresh")
        self.assertEqual(len(seen), 1)


class TestMutationHooks(unittest.TestCase):
    def test_after_mutation_busts_and_blocks(self):
        rc = fresh_cache(AMPD_CACHE_TTL="60")
        rc.put("/v1/me/library/songs?limit=100", ["song"])
        self.assertEqual(rc.get("/v1/me/library/songs?limit=100"), ["song"])
        rc.after_mutation()
        self.assertIsNone(rc.get("/v1/me/library/songs?limit=100"),
                          "mutation must bust")
        self.assertTrue(rc.blocked(), "grace window opens")
        seen = []
        rc.coalesce("/v1/me/library/songs?limit=100",
                    lambda: seen.append(1) or ["live"])
        self.assertEqual(len(seen), 1, "reads inside grace must bypass cache")
        # grace expires (shorten the window, don't sleep the real 8s)
        rc._blocked_until = time.time() - 0.01
        self.assertFalse(rc.blocked())

    def test_blocked_reads_never_cache(self):
        rc = fresh_cache(AMPD_CACHE_TTL="60")
        rc.after_mutation()
        rc.coalesce("/k", lambda: "x")
        self.assertIsNone(rc.get("/k"), "grace-window fetch must not populate")


if __name__ == "__main__":
    unittest.main(verbosity=2)
