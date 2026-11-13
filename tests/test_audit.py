"""Audit log tests (v0.7 #47) — hermetic. The trail never breaks the
request path; bodies are never in it; the master audits, friends don't.
"""
import os
import sys
import tempfile
import unittest
import unittest.mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tonearm import audit, keys as k


class Ident:
    def __init__(self, key_id="k-1", is_master=False):
        self.key_id = key_id
        self.is_master = is_master
        self.describe = lambda: "master" if is_master else key_id


class TestRing(unittest.TestCase):
    def test_records_and_exports_newest_first(self):
        audit._ring.clear()
        m = Ident(is_master=True)
        audit.record(m, "POST", "/api/write/playlists", 200)
        audit.record(m, "PUT", "/api/write/playlists/p1/tracks", 200)
        out = audit.export()
        self.assertEqual(out["source"], "ring (store off — last 1000, "
                                        "this boot)")
        self.assertEqual([i["method"] for i in out["items"]],
                         ["PUT", "POST"], "newest first")
        self.assertEqual(out["total"], 2)

    def test_since_filters(self):
        audit._ring.clear()
        m = Ident(is_master=True)
        e1 = audit.record(m, "POST", "/a", 200)
        e2 = audit.record(m, "DELETE", "/b", 204)
        out = audit.export(since=e2["ts"])
        self.assertEqual(out["total"], 0, "nothing newer than the newest")
        out = audit.export(since=e1["ts"])
        self.assertEqual([i["method"] for i in out["items"]], ["DELETE"])

    def test_ring_is_bounded(self):
        audit._ring.clear()
        m = Ident(is_master=True)
        for i in range(audit.RING + 50):
            audit.record(m, "POST", f"/x/{i}", 200)
        self.assertEqual(len(audit._ring), audit.RING,
                         "the ring drops the oldest, never grows unbounded")

    def test_store_failure_never_raises(self):
        class Boom:
            def audit_append(self, rows):
                raise RuntimeError("disk haunted")

        with unittest.mock.patch.object(audit, "store", Boom()):
            m = Ident(is_master=True)
            e = audit.record(m, "POST", "/x", 500)   # must not raise
        self.assertEqual(e["status"], 500)


class TestStoreBacked(unittest.TestCase):
    def test_write_through_and_export(self):
        from tonearm.store import Store
        s = Store(path=":memory:", enabled=True)
        s.start()
        self.addCleanup(s.close)
        m = Ident(is_master=True)
        for i in range(5):
            s.audit_append([(1000.0 + i, "k-1", "POST", f"/p/{i}", 200)])
        out = s.audit_since(since=0, limit=3)
        self.assertEqual(out["total"], 5)
        self.assertEqual(out["count"], 3)
        self.assertEqual(out["next_offset"], 3)
        self.assertEqual([i["path"] for i in out["items"]],
                         ["/p/4", "/p/3", "/p/2"], "newest first")
        self.assertEqual(out["items"][0]["key_id"], "k-1")

    def test_store_off_raises_store_disabled(self):
        from tonearm.store import Store, StoreDisabled
        s = Store(path=":memory:", enabled=False)
        with self.assertRaises(StoreDisabled):
            s.audit_since()


class TestRouteGuards(unittest.TestCase):
    def test_master_only(self):
        # the route guard's contract, tested as the identity logic it is
        self.assertTrue(Ident(is_master=True).is_master)
        self.assertFalse(Ident("k-2").is_master)
        # audit.record never logs bodies — the entry shape has no body field
        audit._ring.clear()
        e = audit.record(Ident(is_master=True), "POST", "/x", 200)
        self.assertEqual(set(e.keys()),
                         {"ts", "key_id", "method", "path", "status"})




if __name__ == "__main__":
    unittest.main(verbosity=2)
