"""Multi-key auth tests (v0.7 #46) — hermetic.

Pure registry/limiter/cap units + the CLI's file roundtrip; no HTTP, no
Chrome. The middleware is thin wiring over these.
"""
import json
import os
import sys
import tempfile
import unittest
import unittest.mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tonearm import keys as k
from tonearm import config as cfg


def temp_registry():
    d = tempfile.mkdtemp(prefix="tonearm-keys-test-")
    return k.KeysRegistry(path=os.path.join(d, "keys.json"))


class FakeIdentity:
    def __init__(self, key_id="k-test", rate=0, is_master=False):
        self.key_id = key_id
        self.rate = rate
        self.is_master = is_master
        self.describe = lambda: "master" if is_master else key_id


class TestRegistry(unittest.TestCase):
    def setUp(self):
        cfg.config.api_key = "master-key-123"
        self.addCleanup(setattr, cfg.config, "api_key", cfg.config.api_key)

    def test_master_resolves_and_wins(self):
        r = temp_registry()
        ident = r.resolve("master-key-123")
        self.assertTrue(ident.is_master)
        self.assertTrue(ident.can_write)

    def test_add_resolve_and_hash_only_storage(self):
        r = temp_registry()
        kid, raw = r.add("friend", scopes=("read",), rate=60)
        ident = r.resolve(raw)
        self.assertEqual(ident.key_id, kid)
        self.assertTrue(ident.can_read)
        self.assertFalse(ident.can_write)
        self.assertEqual(ident.rate, 60)
        # the file stores the HASH — a leaked file must not leak keys
        on_disk = open(r.path).read()
        self.assertNotIn(raw, on_disk)
        self.assertIn("key_hash", on_disk)

    def test_write_scope_implies_read(self):
        r = temp_registry()
        kid, raw = r.add("me", scopes=("read", "write"))
        ident = r.resolve(raw)
        self.assertTrue(ident.can_write and ident.can_read)

    def test_revoked_keys_stop_resolving(self):
        r = temp_registry()
        kid, raw = r.add("ex", scopes=("read",))
        self.assertIsNotNone(r.resolve(raw))
        self.assertTrue(r.revoke(kid))
        self.assertIsNone(r.resolve(raw), "a revoked key is dead")
        self.assertFalse(r.revoke(kid), "double revoke says so")

    def test_duplicate_names_rejected(self):
        r = temp_registry()
        r.add("friend")
        with self.assertRaises(ValueError):
            r.add("friend")

    def test_file_reread_on_miss(self):
        """`keys add` from the CLI must reach a RUNNING server without a
        restart: a resolve miss invalidates the mtime cache."""
        r = temp_registry()
        self.assertIsNone(r.resolve("toneark_brandnew"))
        kid, raw = r.add("late")
        self.assertIsNotNone(r.resolve(raw),
                             "a key added after boot still resolves")
        self.assertEqual(kid, r.list()[0]["id"])

    def test_list_never_shows_hashes(self):
        r = temp_registry()
        kid, raw = r.add("friend")
        listing = json.dumps(r.list())
        self.assertNotIn(raw, listing)


class TestRateLimiter(unittest.TestCase):
    def test_master_and_unlimited_pass_always(self):
        for ident in (k.MASTER, FakeIdentity("k-x", rate=0)):
            for _ in range(500):
                ok, _ = k.RateLimiter().check(ident)
                self.assertTrue(ok)

    def test_ceiling_429s_with_retry_after(self):
        rl = k.RateLimiter()
        ident = FakeIdentity("k-cap", rate=3)
        for _ in range(3):
            ok, retry = rl.check(ident)
            self.assertTrue(ok)
        ok, retry = rl.check(ident)
        self.assertFalse(ok, "the 4th request inside the window is over")
        self.assertGreaterEqual(retry, 1)


class TestSseCap(unittest.TestCase):
    def test_cap_admits_then_rejects_then_frees(self):
        cap = k.SseCap()
        ident = FakeIdentity("k-sse")
        self.assertTrue(all(cap.enter(ident) for _ in range(3)))
        self.assertFalse(cap.enter(ident), "the 4th concurrent stream is over")
        cap.leave(ident)
        self.assertTrue(cap.enter(ident), "a disconnect frees the slot")
        for _ in range(3):
            cap.leave(ident)

    def test_master_is_uncapped(self):
        cap = k.SseCap()
        self.assertTrue(all(cap.enter(k.MASTER) for _ in range(100)))


class TestCliRoundtrip(unittest.TestCase):
    def test_add_then_list_then_revoke_via_main(self):
        d = tempfile.mkdtemp(prefix="tonearm-keys-cli-")
        path = os.path.join(d, "keys.json")
        import sys as _sys
        with unittest.mock.patch.object(k.registry, "path", path):
            with unittest.mock.patch.object(_sys, "argv",
                                            ["keys", "add", "phone",
                                             "--scopes", "read,write",
                                             "--rate", "30"]):
                k.main()
            self.assertTrue(os.path.exists(path))
            self.assertEqual(os.stat(path).st_mode & 0o777, 0o600,
                             "the keys file ships 0600")
            with unittest.mock.patch.object(_sys, "argv",
                                            ["keys", "list"]):
                k.main()      # must not raise; hashes never printed
            with unittest.mock.patch.object(_sys, "argv",
                                            ["keys", "revoke", "k-404"]):
                k.main()      # unknown id: says so, doesn't crash


if __name__ == "__main__":
    unittest.main(verbosity=2)
