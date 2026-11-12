"""Unit tests for listening stats + scheduled exports (v0.3 #28 #29).

Run:  python3 -m unittest discover -s tests
"""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tonearm.store import Store
from tonearm.exporter import build_export, write_atomic, prune, ExportScheduler


def temp_store():
    d = tempfile.mkdtemp(prefix="tonearm-stats-test-")
    return Store(path=os.path.join(d, "test.db"), enabled=True)


class TestStats(unittest.TestCase):
    def _seed(self, s):
        T0 = 1700000000.0
        # day 0: track A x3, track B x1  | day 1: track A x1, artist C x2
        s.record_play("ta", "Track A", "Artist One", "Al", None, 100,
                      T0)
        s.record_play("ta", "Track A", "Artist One", "Al", None, 100,
                      T0 + 60)
        s.record_play("tb", "Track B", "Artist One", "Al", None, 100,
                      T0 + 120)
        s.record_play("ta", "Track A", "Artist One", "Al", None, 100,
                      T0 + 86400)
        s.record_play("tc", "Track C", "Artist Two", "Al2", None, 100,
                      T0 + 86400 + 60)
        s.record_play("tc", "Track C", "Artist Two", "Al2", None, 100,
                      T0 + 86400 + 120)
        return T0

    def test_top_tracks_and_artists(self):
        s = temp_store()
        s.start()
        try:
            T0 = self._seed(s)
            out = s.stats(since=0)
            self.assertEqual(out["total_plays"], 6)
            self.assertEqual(out["top_tracks"][0]["id"], "ta")
            self.assertEqual(out["top_tracks"][0]["plays"], 3)
            artists = {a["artist"]: a["plays"] for a in out["top_artists"]}
            self.assertEqual(artists, {"Artist One": 4, "Artist Two": 2})
            # window: only the second day
            out = s.stats(since=T0 + 86400)
            self.assertEqual(out["total_plays"], 3)
        finally:
            s.close()

    def test_series_buckets_per_day(self):
        s = temp_store()
        s.start()
        try:
            T0 = self._seed(s)
            series = s.plays_series(since=0)
            days = {d["day"]: d["plays"] for d in series}
            self.assertEqual(sum(days.values()), 6)
            self.assertEqual(len(days), 2, "two distinct UTC days")
            self.assertEqual(list(days.values())[-1], 3)
        finally:
            s.close()

    def test_dedupe_is_the_writers_guarantee(self):
        s = temp_store()
        s.start()
        try:
            s.record_play("tx", "X", "A", "Al", None, 1, 1700000000.0)
            s.record_play("tx", "X", "A", "Al", None, 1, 1700000000.0)
            self.assertEqual(s.stats(since=0)["total_plays"], 1,
                             "double-writes are impossible by schema")
        finally:
            s.close()


class TestExporter(unittest.TestCase):
    def test_build_export_shape(self):
        class FakeMK:
            def paginated(self, path, extract):
                if "songs" in path:
                    return [{"id": "i.1", "attributes": {"name": "S"}},
                            {"id": "i.2", "attributes": {"name": "T"}}]
                return [{"id": "p.1", "attributes": {"name": "P"}}]

            def song_row(self, t):
                return {"id": t["id"]}

            def playlist_tracks(self, pid):
                return [{"id": "i.1", "attributes": {}}]
        out = build_export(FakeMK())
        self.assertEqual(out["song_count"], 2)
        self.assertEqual(out["playlist_count"], 1)
        self.assertEqual(out["playlists"][0]["tracks"][0]["id"], "i.1")
        self.assertIn("exported_at", out)

    def test_atomic_write(self):
        d = tempfile.mkdtemp()
        path = os.path.join(d, "export-test.json")
        write_atomic(path, {"a": 1})
        with open(path) as f:
            self.assertEqual(json.load(f), {"a": 1})
        leftovers = [f for f in os.listdir(d) if ".tmp-" in f]
        self.assertEqual(leftovers, [], "no tmp litter after a clean write")

    def test_prune_keeps_n(self):
        d = tempfile.mkdtemp()
        for i in range(5):
            write_atomic(os.path.join(d, f"export-2026010{i}-000000.json"),
                         {"i": i})
        write_atomic(os.path.join(d, "other.json"), {})   # never matched
        removed = prune(d, keep=2)
        self.assertEqual(len(removed), 3)
        left = sorted(f for f in os.listdir(d) if f.startswith("export-"))
        self.assertEqual(len(left), 2, "newest two exports survive")


import json  # noqa: E402  (used by atomic-write test above)


class TestExportScheduler(unittest.TestCase):
    def test_single_flight(self):
        import threading

        class B:
            def health(self):
                return {"last_ok": True, "consecutive_failures": 0}
        gate = threading.Event()
        sched = ExportScheduler(B(), None, interval=3600,
                                build_fn=lambda mk: gate.wait(5) or {},
                                directory=tempfile.mkdtemp())
        out = {}
        t = threading.Thread(target=lambda: out.update(sched.run_export()))
        t.start()
        time.sleep(0.2)
        second = sched.run_export()
        self.assertFalse(second["ran"], "export must refuse to overlap itself")
        gate.set()
        t.join(5)

    def test_stall_gate_skips(self):
        class B:
            def health(self):
                return {"last_ok": False, "consecutive_failures": 3}
        sched = ExportScheduler(B(), None, interval=3600,
                                build_fn=lambda mk: {},
                                directory=tempfile.mkdtemp())
        self.assertTrue(sched._stalled())

    def test_run_records_cursor_when_store_on(self):
        class B:
            def health(self):
                return {"last_ok": True, "consecutive_failures": 0}
        s = temp_store()
        s.start()
        try:
            sched = ExportScheduler(B(), None, interval=3600,
                                    build_fn=lambda mk: {"song_count": 0,
                                                         "playlist_count": 0,
                                                         "playlists": []},
                                    directory=tempfile.mkdtemp(), store=s)
            out = sched.run_export()
            self.assertTrue(out["ran"])
            self.assertEqual(s.get_cursor("export.last_run")["songs"], 0)
        finally:
            s.close()


import time  # noqa: E402  (used by the scheduler tests above)

if __name__ == "__main__":
    unittest.main(verbosity=2)
