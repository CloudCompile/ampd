"""Unit tests for the local store (v0.3 Memory) — no Chrome, no network.

Run:  python3 -m unittest discover -s tests
Everything here is hermetic: real sqlite files in a temp dir.
"""
import os
import sys
import tempfile
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tonearm.store import Store, StoreDisabled, diff_rows, HistoryWriter


def temp_store():
    d = tempfile.mkdtemp(prefix="tonearm-store-test-")
    return Store(path=os.path.join(d, "test.db"), enabled=True)


class TestPlays(unittest.TestCase):
    def test_dedupe_on_track_and_started_at(self):
        s = temp_store()
        s.start()
        try:
            s.record_play("1440819066", "T1", "A", "Al", None, 200000,
                          1700000000.0)
            s.record_play("1440819066", "T1", "A", "Al", None, 200000,
                          1700000000.0)  # same play twice — restart/drain overlap
            out = s.recently_played()
            self.assertEqual(out["total"], 1, "dedupe on (track_id, started_at)")
        finally:
            s.close()

    def test_newest_first_and_pagination(self):
        s = temp_store()
        s.start()
        try:
            for i in range(5):
                s.record_play(f"t{i}", f"track{i}", "a", "al", None, 1000,
                              1700000000.0 + i * 10)
            page1 = s.recently_played(limit=2)
            self.assertEqual([i["title"] for i in page1["items"]],
                             ["track4", "track3"], "newest first")
            self.assertEqual(page1["total"], 5)
            self.assertEqual(page1["next_offset"], 2)
            page2 = s.recently_played(limit=2, offset=page1["next_offset"])
            self.assertEqual([i["title"] for i in page2["items"]],
                             ["track2", "track1"])
            last = s.recently_played(limit=2, offset=4)
            self.assertIsNone(last["next_offset"], "no next past the end")
        finally:
            s.close()

    def test_disabled_raises_StoreDisabled(self):
        s = Store(path="/tmp/should-never-open.db", enabled=False)
        with self.assertRaises(StoreDisabled):
            s.recently_played()


class TestCursors(unittest.TestCase):
    def test_roundtrip_and_default(self):
        s = temp_store()
        s.start()
        try:
            self.assertIsNone(s.get_cursor("nope"))
            self.assertEqual(s.get_cursor("nope", default=42), 42)
            s.set_cursor("lib.sync.last_run", {"ts": 123})
            self.assertEqual(s.get_cursor("lib.sync.last_run"), {"ts": 123})
            s.set_cursor("lib.sync.last_run", {"ts": 456})
            self.assertEqual(s.get_cursor("lib.sync.last_run"), {"ts": 456},
                             "cursor overwrite wins")
        finally:
            s.close()


class TestLibraryRows(unittest.TestCase):
    ROW = dict(library_id="i.abc", catalog_id="1440", name="Song", artist="A",
               album="Al", duration_ms=1000, kind="library-songs",
               attributes={"playCount": 0})

    def _row(self, **kw):
        return {**self.ROW, **kw}

    def test_insert_then_noop_then_change(self):
        s = temp_store()
        s.start()
        try:
            s.upsert_library_rows([self._row()])
            row = s.library_rows()[0]
            first_changed = row["last_changed"]
            self.assertEqual(row["first_seen"], first_changed)

            time.sleep(0.01)
            s.upsert_library_rows([self._row()])   # identical — nothing changed
            row = s.library_rows()[0]
            self.assertEqual(row["last_changed"], first_changed,
                             "identical re-walk must not bump last_changed")

            time.sleep(0.01)
            s.upsert_library_rows([self._row(name="Song (Live)")])
            row = s.library_rows()[0]
            self.assertGreater(row["last_changed"], first_changed,
                               "a real change bumps last_changed")
            self.assertEqual(row["name"], "Song (Live)")
        finally:
            s.close()

    def test_catalog_id_backfill_counts_as_change(self):
        s = temp_store()
        s.start()
        try:
            s.upsert_library_rows([self._row(catalog_id=None)])
            s.upsert_library_rows([self._row(catalog_id="999")])
            row = s.library_rows()[0]
            self.assertEqual(row["catalog_id"], "999",
                             "fresh rows lacking catalog ids get backfilled")
        finally:
            s.close()


class TestDiff(unittest.TestCase):
    def test_added_updated_removed(self):
        T = 1700000000.0
        before = [dict(library_id="i.1", name="kept", artist="a", album="l",
                       first_seen=T - 100, last_seen=T - 10,
                       last_changed=T - 100),
                  dict(library_id="i.2", name="gone", artist="a", album="l",
                       first_seen=T - 100, last_seen=T - 10,
                       last_changed=T - 100),
                  dict(library_id="i.3", name="edited", artist="a", album="l",
                       first_seen=T - 100, last_seen=T - 10,
                       last_changed=T - 100)]
        after = [dict(library_id="i.1", name="kept", artist="a", album="l",
                      first_seen=T - 100, last_seen=T + 5,
                      last_changed=T - 100),
                 dict(library_id="i.3", name="edited!", artist="a", album="l",
                      first_seen=T - 100, last_seen=T + 5,
                      last_changed=T + 5),
                 dict(library_id="i.4", name="new", artist="a", album="l",
                      first_seen=T + 5, last_seen=T + 5, last_changed=T + 5)]
        out = diff_rows(before, after, before_ts=T, after_ts=T + 10)
        self.assertEqual([r["library_id"] for r in out["added"]], ["i.4"])
        self.assertEqual([r["library_id"] for r in out["updated"]], ["i.3"],
                         "only real changes, not the re-walked crowd")
        self.assertEqual([r["library_id"] for r in out["removed"]], ["i.2"])

    def test_rows_without_library_id_fall_to_name_key(self):
        T = 100.0
        out = diff_rows([], [], T, T + 1)
        self.assertEqual(out, {"added": [], "updated": [], "removed": [],
                               "since": T, "until": T + 1})


class FakeStore:
    """Records record_play calls without any sqlite."""

    def __init__(self):
        self.played = []

    def record_play(self, **kw):
        self.played.append(kw)


def ev(seq, ev_name, track_id, title, ts, playing=True):
    return {"seq": seq, "ev": ev_name, "id": track_id, "title": title,
            "artist": "a", "album": "al", "artworkUrl": None,
            "durationMs": 1000, "ts": ts, "isPlaying": playing}


class TestHistoryWriter(unittest.TestCase):
    def test_track_starts_only(self):
        w = HistoryWriter(FakeStore(), None, None)
        T = 1700000000000
        w.process_events([
            ev(1, "playbackProgressDidChange", "t1", "Song A", T),
            ev(2, "playbackProgressDidChange", "t1", "Song A", T + 5000),
            ev(3, "playbackStateDidChange", "t1", "Song A", T + 6000,
               playing=False),                       # pause — same track
            ev(4, "nowPlayingItemDidChange", "t2", "Song B", T + 10000),
            ev(5, "playbackStateDidChange", "t2", "Song B", T + 11000),
        ])
        titles = [p["title"] for p in w.store.played]
        self.assertEqual(titles, ["Song A", "Song B"],
                         "progress ticks and same-track state changes are "
                         "not plays")

    def test_resume_from_pause_counts(self):
        w = HistoryWriter(FakeStore(), None, None)
        T = 1700000000000
        w.process_events([ev(1, "playbackProgressDidChange", "t1", "S", T)])
        w.process_events([ev(2, "playbackStateDidChange", "t1", "S", T + 1,
                             playing=False)])
        w.process_events([ev(3, "playbackStateDidChange", "t1", "S", T + 2)])
        titles = [p["title"] for p in w.store.played]
        self.assertEqual(titles, ["S", "S"],
                         "pause->play of the same track is a new start")

    def test_seq_advances_even_on_skipped_events(self):
        w = HistoryWriter(FakeStore(), None, None)
        T = 1700000000000
        w.process_events([ev(1, "playbackProgressDidChange", "t1", "S", T)])
        w.process_events([ev(2, "playbackStateDidChange", "t1", "S", T + 1,
                             playing=False)])
        self.assertEqual(w._seq, 2, "cursor must advance past skipped events")

    def test_stalled_renderer_skips_ticks(self):
        class FakeBrowser:
            def health(self):
                return {"running": True, "last_ok": False,
                        "consecutive_failures": 2}
        w = HistoryWriter(FakeStore(), FakeBrowser(), None)
        self.assertTrue(w._stalled())

        class OkBrowser:
            def health(self):
                return {"running": True, "last_ok": True,
                        "consecutive_failures": 0}
        w2 = HistoryWriter(FakeStore(), OkBrowser(), None)
        self.assertFalse(w2._stalled())

    def test_cold_renderer_counts_as_available(self):
        class ColdBrowser:
            def health(self):
                return {"running": False, "last_ping_ts": None,
                        "last_ok": None, "consecutive_failures": 0}
        w = HistoryWriter(FakeStore(), ColdBrowser(), None)
        self.assertFalse(w._stalled(),
                         "a never-connected renderer must let background "
                         "work trigger the first connect — otherwise every "
                         "thread politely waits on the watchdog forever")


class TestSnapshotScheduler(unittest.TestCase):
    def _sched(self, store, walk_rows_fn, browser=None):
        from tonearm.store import SnapshotScheduler
        return SnapshotScheduler(store, browser or FakeOkBrowser(), None,
                                 interval=3600, walk_fn=walk_rows_fn)

    def test_walk_upserts_and_records_cursor(self):
        s = temp_store()
        s.start()
        try:
            rows = [dict(library_id="i.1", name="A", artist="x", album="l",
                         catalog_id=None, duration_ms=1, type="library-songs",
                         attributes={}),
                    dict(library_id="i.2", name="B", artist="x", album="l",
                         catalog_id="99", duration_ms=2, type="library-songs",
                         attributes={})]
            sched = self._sched(s, lambda: rows)
            out = sched.run_walk()
            self.assertTrue(out["ran"])
            self.assertEqual(out["rows"], 2)
            self.assertEqual(s.library_count(), 2)
            self.assertEqual(s.get_cursor("library.walk")["rows"], 2,
                             "cursor records the completed walk")
        finally:
            s.close()

    def test_walk_never_overlaps_itself(self):
        import threading
        s = temp_store()
        s.start()
        try:
            gate = threading.Event()
            def slow_walk():
                gate.wait(5)          # first walk still running
                return []
            sched = self._sched(s, slow_walk)
            t = threading.Thread(target=sched.run_walk, daemon=True)
            t.start()
            time.sleep(0.2)
            out = sched.run_walk()    # second call while first is in flight
            self.assertFalse(out["ran"], "single-flight: must refuse to overlap")
            gate.set()
            t.join(5)
        finally:
            s.close()

    def test_removal_visible_after_next_walk(self):
        s = temp_store()
        s.start()
        try:
            def mkrows(ids):
                return [dict(library_id=i, name=f"n{i}", artist="x", album="l",
                             catalog_id=None, duration_ms=1,
                             type="library-songs", attributes={})
                        for i in ids]
            sched = self._sched(s, lambda: mkrows(["i.1", "i.2", "i.3"]))
            sched.run_walk()
            after_walk1 = s.library_rows()
            since = max(r["last_seen"] for r in after_walk1)

            sched._walk_fn = lambda: mkrows(["i.1"])   # 2 and 3 vanished
            sched.run_walk()
            diff = {"added": s.library_added_since(since)["items"],
                    "removed": s.library_removed_since(since)["items"]}
            self.assertEqual([r["library_id"] for r in diff["removed"]],
                             ["i.2", "i.3"],
                             "gone rows keep their old last_seen — the diff "
                             "sees the removal")
            self.assertEqual(diff["added"], [])
        finally:
            s.close()


class FakeOkBrowser:
    def health(self):
        return {"running": True, "last_ok": True, "consecutive_failures": 0}


class TestDiffQueries(unittest.TestCase):
    def test_added_updated_removed_queries(self):
        s = temp_store()
        s.start()
        try:
            # seed directly with controlled watermarks
            s.upsert_library_rows([
                dict(library_id="i.a", name="old", artist="x", album="l",
                     catalog_id=None, duration_ms=1, type=None,
                     attributes={})])
            first = s.library_rows()[0]
            time.sleep(0.01)
            boundary = time.time()
            time.sleep(0.01)
            # brand new row + a change to the old one
            s.upsert_library_rows([
                dict(library_id="i.a", name="old!", artist="x", album="l",
                     catalog_id=None, duration_ms=1, type=None,
                     attributes={}),
                dict(library_id="i.b", name="new", artist="x", album="l",
                     catalog_id=None, duration_ms=1, type=None,
                     attributes={})])
            self.assertEqual(
                [r["library_id"] for r in
                 s.library_added_since(boundary)["items"]], ["i.b"])
            self.assertEqual(
                [r["library_id"] for r in
                 s.library_updated_since(boundary)["items"]], ["i.a"],
                 "changed row is an update, not an add")
            self.assertEqual(
                [r["library_id"] for r in
                 s.library_removed_since(0)["items"]], [],
                "nothing predates zero — no removals")
            # since=0 -> everything is an add
            self.assertEqual(s.library_added_since(0)["total"], 2)
        finally:
            s.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
