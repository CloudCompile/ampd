"""Smart-playlist engine tests (v0.6 #44) — hermetic.

Evaluation is pure and local (no Apple, no threads); materialization is
writes-gated, one find-or-create + one full-list PUT.
"""
import os
import sys
import unittest
import unittest.mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tonearm import smartlists as sl
from tonearm import config as cfg


NOW = 1800000000.0


def row(n, name=None, artist="Artist", album="Album", plays=None,
        release="2024-01-01", first_seen=1000.0, genres=None):
    attrs = {"name": name or f"Track {n}", "releaseDate": release}
    if plays is not None:
        attrs["playCount"] = plays
    if genres is not None:
        attrs["genreNames"] = genres
    return {"library_id": f"i.{n}", "catalog_id": f"c.{n}",
            "name": name or f"Track {n}", "artist": artist, "album": album,
            "first_seen": first_seen, "attributes": attrs}


NEW_ADD = 1780000000.0          # ~2026-06, "recently added" in these tests

ROWS = [
    row(1, "Deep Blue", artist="Aurora", plays=5, release="2020-01-01",
        first_seen=1000.0, genres=["Electronica"]),
    row(2, "Skyline", artist="Aurora", plays=0, release="2026-02-02",
        first_seen=NEW_ADD, genres=["Electronica"]),
    row(3, "Dirt Road", artist="Hank", plays=12, release="2015-07-07",
        first_seen=1000.0, genres=["Country"]),
    row(4, "Never Played", artist="Aurora", plays=None,
        first_seen=NEW_ADD),
]

LAST_PLAYED = {"i.1": NOW - 2 * 86400, "c.1": NOW - 2 * 86400,
               "i.3": NOW - 90 * 86400, "c.3": NOW - 90 * 86400}


class TestEvaluate(unittest.TestCase):
    def test_string_rules_are_case_insensitive(self):
        m = sl.evaluate(ROWS, [{"field": "artist", "op": "contains",
                                "value": "aurora"}], now=NOW)
        self.assertEqual([x["library_id"] for x in m],
                         ["i.1", "i.2", "i.4"])
        m = sl.evaluate(ROWS, [{"field": "title", "op": "starts",
                                "value": "deep"}], now=NOW)
        self.assertEqual([x["name"] for x in m], ["Deep Blue"])

    def test_play_count_rules_and_absent_data(self):
        m = sl.evaluate(ROWS, [{"field": "play_count", "op": "gte",
                                "value": 5}], now=NOW)
        self.assertEqual([x["library_id"] for x in m], ["i.1", "i.3"])
        m = sl.evaluate(ROWS, [{"field": "play_count", "op": "eq",
                                "value": 0}], now=NOW)
        self.assertEqual([x["library_id"] for x in m], ["i.2"],
                         "never-played-without-count is NOT zero plays")

    def test_last_played_joins_both_id_spaces(self):
        m = sl.evaluate(ROWS, [{"field": "last_played", "op": "within_days",
                                "value": 7}], last_played=LAST_PLAYED,
                        now=NOW)
        self.assertEqual([x["library_id"] for x in m], ["i.1"])
        m = sl.evaluate(ROWS, [{"field": "last_played",
                                "op": "older_than_days", "value": 30}],
                        last_played=LAST_PLAYED, now=NOW)
        self.assertEqual([x["library_id"] for x in m], ["i.2", "i.3", "i.4"],
                         "'not played in 30 days' includes never-played "
                         "(vacuously) — AND with play_count to exclude")
        m = sl.evaluate(ROWS, [{"field": "last_played", "op": "never"}],
                        last_played=LAST_PLAYED, now=NOW)
        self.assertEqual([x["library_id"] for x in m], ["i.2", "i.4"])

    def test_added_and_release_date_rules(self):
        m = sl.evaluate(ROWS, [{"field": "added", "op": "after",
                                "value": "2026-01-01"}],
                        last_played=LAST_PLAYED, now=NOW)
        self.assertEqual([x["library_id"] for x in m], ["i.2", "i.4"],
                         "added reads the store watermark first_seen")
        m = sl.evaluate(ROWS, [{"field": "release_date", "op": "after",
                                "value": "2025-01-01"}],
                        last_played=LAST_PLAYED, now=NOW)
        self.assertEqual([x["library_id"] for x in m], ["i.2"])

    def test_rules_anded_together(self):
        m = sl.evaluate(ROWS, [
            {"field": "artist", "op": "equals", "value": "aurora"},
            {"field": "play_count", "op": "gt", "value": 0}],
            last_played=LAST_PLAYED, now=NOW)
        self.assertEqual([x["library_id"] for x in m], ["i.1"])

    def test_sorts(self):
        s = sl.sort_rows(ROWS, "added_desc")
        self.assertEqual([x["library_id"] for x in s][:2], ["i.2", "i.4"])
        s = sl.sort_rows(ROWS, "play_count_desc")
        self.assertEqual(s[0]["library_id"], "i.3")
        s = sl.sort_rows(ROWS, "release_date_desc")
        self.assertEqual(s[0]["library_id"], "i.2")
        s = sl.sort_rows(ROWS, "name")
        self.assertEqual(s[0]["library_id"], "i.1")

    def test_validation_rejects_unknown_fields_and_ops(self):
        with self.assertRaises(sl.SmartlistError):
            sl.validate_rules([{"field": "bogus", "op": "contains",
                                "value": "x"}])
        with self.assertRaises(sl.SmartlistError):
            sl.validate_rules([{"field": "play_count", "op": "contains",
                                "value": 1}])
        with self.assertRaises(sl.SmartlistError):
            sl.validate_rules([{"field": "title", "op": "contains"}])
        with self.assertRaises(sl.SmartlistError):
            sl.validate_sort("random")
        self.assertEqual(sl.validate_rules(None), [])


class FakeBrowser:
    def __init__(self, health):
        self._h = health

    def health(self):
        return self._h


class FakeStore:
    def set_cursor(self, name, value):
        pass

    def get_cursor(self, name, default=None):
        return default


class TestMaterialize(unittest.TestCase):
    def _sl(self, playlist_id=None):
        return {"id": "sl-1", "name": "Aurora Rotator", "rules": [
            {"field": "artist", "op": "equals", "value": "aurora"}],
            "sort": "play_count_desc", "limit": 2,
            "playlist_id": playlist_id, "refresh_s": 300}

    def test_materialize_creates_then_puts_the_full_list(self):
        from tonearm.store import Store
        store = Store(path=":memory:", enabled=True)
        store.start()
        self.addCleanup(store.close)
        store.upsert_library_rows([{
            "library_id": f"i.{n}", "catalog_id": f"c.{n}",
            "name": f"T{n}", "artist": "Aurora", "album": "A",
            "duration_ms": 1, "type": "library-songs",
            "attributes": {"playCount": n},
        } for n in (1, 2, 3)])
        # the definition lives in the store like the routes would create it
        store.smartlist_add("sl-1", "Aurora Rotator", "",
                            [{"field": "artist", "op": "equals",
                              "value": "aurora"}], "play_count_desc", 2, 300)

        calls = []

        class FakeMk:
            def find_library_playlist(self, name):
                calls.append(("find", name))
                return None

            def playlist_create(self, name, description=""):
                calls.append(("create", name))
                return "p.new"

            def playlist_set_tracks(self, pid, library_ids):
                calls.append(("put", pid, tuple(library_ids)))
                return 200

        with unittest.mock.patch.object(cfg.config, "enable_writes", True):
            out = sl.materialize_list(self._sl(), store=store,
                                      mk_mod=FakeMk())
        self.assertEqual(calls[0], ("find", "Aurora Rotator"))
        self.assertEqual(calls[1], ("create", "Aurora Rotator"))
        # full-list PUT: top-2 by play count, library ids, one call
        self.assertEqual(calls[2], ("put", "p.new", ("i.3", "i.2")))
        self.assertEqual(out["count"], 2)
        self.assertTrue(out["created"])
        stored = store.smartlist_get("sl-1")
        self.assertEqual(stored["playlist_id"], "p.new")
        self.assertEqual(stored["last_count"], 2)

    def test_materialize_is_writes_gated(self):
        from tonearm.store import Store
        store = Store(path=":memory:", enabled=True)
        store.start()
        self.addCleanup(store.close)
        with unittest.mock.patch.object(cfg.config, "enable_writes", False):
            with self.assertRaises(sl.SmartlistWritesDisabled):
                sl.materialize_list(self._sl(), store=store)


class TestScheduler(unittest.TestCase):
    def test_run_once_skips_writes_when_gate_is_off(self):
        class FakeListStore(FakeStore):
            def library_rows(self):
                return []

            def smartlist_rows(self):
                return [{"id": "sl-1", "name": "x", "rules": [],
                         "sort": "added_desc", "limit": 0, "refresh_s": 300,
                         "playlist_id": None, "last_sync": None}]

            def smartlist_update(self, list_id, **fields):
                assert "last_sync" not in fields, \
                    "no Apple touch without the writes gate"

        sched = sl.SmartlistScheduler(FakeListStore(), FakeBrowser({}),
                                      interval=60,
                                      materialize_fn=self.fail)
        with unittest.mock.patch.object(cfg.config, "enable_writes", False), \
                unittest.mock.patch.object(sl, "last_played_index",
                                           lambda store: {}):
            out = sched.run_once()
        self.assertEqual(out["skipped_writes"], 1)

    def test_run_once_throttles_fresh_syncs(self):
        class FakeListStore(FakeStore):
            def smartlist_rows(self):
                return [{"id": "sl-1", "name": "x", "rules": [],
                         "sort": "added_desc", "limit": 0, "refresh_s": 3600,
                         "playlist_id": "p.1",
                         "last_sync": NOW - 60}]     # synced a minute ago

        sched = sl.SmartlistScheduler(FakeListStore(), FakeBrowser({}),
                                      interval=60,
                                      materialize_fn=self.fail)
        with unittest.mock.patch.object(cfg.config, "enable_writes", True):
            with unittest.mock.patch.object(sl.time, "time", lambda: NOW):
                out = sched.run_once()
        self.assertEqual(out["throttled"], 1, "the refresh floor holds")
        self.assertEqual(out["synced"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
