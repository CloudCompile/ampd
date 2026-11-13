"""New-release watcher tests (v0.6 #42) — hermetic.

The whole point: the FIRST pass is a silent baseline (never a flood of
"new" on a fresh start), a genuinely newer release emits exactly one
`release.found`, and every Apple touch rides existing eval surfaces.
"""
import os
import sys
import time
import unittest
import unittest.mock
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tonearm import watcher as w
from tonearm.watcher import ReleaseWatcher, name_candidates, norm_name, \
    newest_album, _date_gt


def artist(n, name):
    return {"id": f"r.{n}", "library_id": f"r.{n}", "type": "library-artists",
            "name": name, "attributes": {"name": name}}


ARTISTS = [artist(1, "Aurora"), artist(2, "Múm"), artist(3, "Nobody Real")]

# catalog search hits — strict name match or nothing
SEARCH_HITS = {
    "aurora": [{"id": "1470", "type": "artists",
                "attributes": {"name": "Aurora"}}],
    "mum": [{"id": "990", "attributes": {"name": "The Múm"}},   # wrong name
            {"id": "991", "attributes": {"name": "Múm"}}],
}

CATALOG_ALBUMS = {
    "1470": [{"id": "1770", "attributes": {"name": "Old Album",
                                           "releaseDate": "2020-01-01"}}],
    "991": [{"id": "1991", "attributes": {"name": "First LP",
                                          "releaseDate": "2024-05-01"}}],
}


class FakeStore:
    """The watcher-state slice of the store, in memory."""

    def __init__(self):
        self.rows = {}
        self.cursors = {}

    def watcher_artist(self, artist_id):
        return self.rows.get(artist_id)

    def watcher_upsert_artist(self, artist_id, artist_name, **fields):
        row = self.rows.setdefault(artist_id, {"artist_id": artist_id})
        row["artist_name"] = artist_name
        for k, v in fields.items():
            if v is not None:
                row[k] = v
        return row

    def watcher_artists(self):
        return list(self.rows.values())

    def set_cursor(self, name, value):
        self.cursors[name] = value

    def get_cursor(self, name, default=None):
        return self.cursors.get(name, default)


class FakeMk:
    """item_row/paginated/api_music — the real call shapes, fake data."""

    item_row = staticmethod(lambda t: t)

    def paginated(self, path, extract, fresh=False):
        assert "library/artists" in path
        return extract({"data": ARTISTS})

    def api_music(self, path):
        if "term=" in path:
            # the real API matches names accent-insensitively — mirror that
            term = urllib.parse.unquote(
                path.split("term=")[1].split("&")[0])
            hits = next((v for k, v in SEARCH_HITS.items()
                         if norm_name(k) == norm_name(term)), [])
            return {"results": {"artists": {"data": hits}}}
        if "/artists/" in path and "/albums" in path:
            aid = path.split("/artists/")[1].split("/")[0]
            return {"data": CATALOG_ALBUMS.get(aid, [])}
        return {}


def make_watcher(store=None, mk=None, emit=None, **kw):
    kw.setdefault("interval", 3600)
    return ReleaseWatcher(store or FakeStore(), FakeBrowser({}),
                          mk or FakeMk(), emit_fn=emit or (lambda t, d: None),
                          **kw)


class FakeBrowser:
    def __init__(self, health):
        self._h = health

    def health(self):
        return self._h


class TestHelpers(unittest.TestCase):
    def test_norm_name_is_ciaccent_and_punct_insensitive(self):
        self.assertEqual(norm_name("Beyoncé"), norm_name("beyonce"))
        self.assertEqual(norm_name("  AC/DC! "), norm_name("ac dc"))
        self.assertNotEqual(norm_name("The Weeknd"), norm_name("Weeknd"))

    def test_newest_album_prefers_the_latest_date(self):
        albums = [{"id": "a", "attributes": {"name": "Old",
                                             "releaseDate": "2020-01-01"}},
                  {"id": "b", "attributes": {"name": "New",
                                             "releaseDate": "2026-02-02"}},
                  {"id": "c", "attributes": {"name": "No date"}}]
        self.assertEqual(newest_album(albums)["id"], "b")
        self.assertIsNone(newest_album([{"id": "c",
                                         "attributes": {"name": "x"}}]),
                          "no dates = no guess")

    def test_date_gt(self):
        self.assertTrue(_date_gt("2026-02-02", "2026-01-01"))
        self.assertFalse(_date_gt("2026-01-01", "2026-02-02"))
        self.assertFalse(_date_gt("2026-01-01", "2026-01-01"))
        self.assertTrue(_date_gt("2026-01-01", None))


class TestPass(unittest.TestCase):
    def test_first_pass_is_a_silent_baseline(self):
        store, seen = FakeStore(), []
        watcher = make_watcher(store=store,
                               emit=lambda t, d: seen.append((t, d)))
        summary = watcher.run_pass()
        self.assertEqual(seen, [], "a fresh watcher must not fake releases")
        self.assertEqual(summary["new_releases"], 0)
        self.assertEqual(summary["checked"], 3)
        # state recorded, mapped via strict name search
        self.assertEqual(store.rows["r.1"]["catalog_artist_id"], "1470")
        self.assertEqual(store.rows["r.2"]["catalog_artist_id"], "991",
                         "the wrong-name hit is skipped, the exact one wins")
        self.assertIn("r.3", store.rows)      # unmapped: recorded, honest
        self.assertEqual(summary["unmapped"], 1)

    def test_newer_release_emits_exactly_once(self):
        store, seen = FakeStore(), []
        watcher = make_watcher(store=store,
                               emit=lambda t, d: seen.append((t, d)))
        watcher.run_pass()                     # baseline
        new_album = {"id": "1888",
                     "attributes": {"name": "New LP",
                                    "releaseDate": "2026-06-01"}}
        CATALOG_ALBUMS["1470"].insert(0, new_album)
        try:
            summary = watcher.run_pass()
        finally:
            CATALOG_ALBUMS["1470"].remove(new_album)
        self.assertEqual(summary["new_releases"], 1)
        self.assertEqual(len(seen), 1, "one event, not one per pass")
        event_type, payload = seen[0]
        self.assertEqual(event_type, "release.found")
        self.assertEqual(payload["album_id"], "1888")
        self.assertEqual(payload["previous"]["album_id"], "1770")
        # the state advanced: a THIRD pass sees nothing again
        self.assertEqual(watcher.run_pass()["new_releases"], 0)
        self.assertEqual(len(seen), 1)

    def test_older_or_equal_albums_never_emit(self):
        store, seen = FakeStore(), []
        watcher = make_watcher(store=store,
                               emit=lambda t, d: seen.append((t, d)))
        watcher.run_pass()
        # a different album id, but NOT a newer date — no announcement
        old_reissue = {"id": "1770b",
                       "attributes": {"name": "Remaster?",
                                      "releaseDate": "2019-01-01"}}
        CATALOG_ALBUMS["1470"].insert(0, old_reissue)
        try:
            summary = watcher.run_pass()
        finally:
            CATALOG_ALBUMS["1470"].remove(old_reissue)
        self.assertEqual(summary["new_releases"], 0)
        self.assertEqual(seen, [])

    def test_pass_is_bounded(self):
        watcher = make_watcher(max_artists=2)
        summary = watcher.run_pass()
        self.assertEqual(summary["checked"], 2)
        self.assertTrue(summary.get("skipped_budget"))

    def test_pass_is_single_flight(self):
        watcher = make_watcher()
        with watcher._busy:
            summary = watcher.run_pass()
        self.assertFalse(summary["ran"])

    def test_stall_gate(self):
        stalled = ReleaseWatcher(FakeStore(), FakeBrowser(
            {"last_ok": False, "consecutive_failures": 2}), FakeMk(),
            interval=3600)
        self.assertTrue(stalled._stalled())


class TestNameCandidates(unittest.TestCase):
    def test_collab_strings_fall_back_to_the_primary_artist(self):
        self.assertEqual(name_candidates("Alan Walker & Ava Max"),
                         ["Alan Walker & Ava Max", "Alan Walker"])
        self.assertEqual(name_candidates("Adb.nts44, BXN$HEE & Anitor"),
                         ["Adb.nts44, BXN$HEE & Anitor", "Adb.nts44"])
        self.assertEqual(name_candidates("Ado feat. Hatsune Miku"),
                         ["Ado feat. Hatsune Miku", "Ado"])
        self.assertEqual(name_candidates("ABBA"), ["ABBA"],
                         "solo names get one candidate")

    def test_primary_artist_mapping_lands_in_the_store(self):
        SEARCH_HITS["alan walker"] = [
            {"id": "4000", "attributes": {"name": "Alan Walker"}}]
        store, seen = FakeStore(), []
        watcher = make_watcher(store=store,
                               emit=lambda t, d: seen.append((t, d)))
        ARTISTS.append(artist(4, "Alan Walker & Ava Max"))
        try:
            summary = watcher.run_pass()
        finally:
            ARTISTS.pop()
        self.assertEqual(summary["mapped"], 3,
                         "r.1 + r.2 + the collab mapped via its primary artist")
        self.assertEqual(summary["unmapped"], 1)   # Nobody Real, as always
        self.assertEqual(store.rows["r.4"]["catalog_artist_id"], "4000")


class TestAutoAdd(unittest.TestCase):
    def _with_auto_add(self, enable_writes):
        from tonearm import config as cfg
        store, events = FakeStore(), []

        class AddMk(FakeMk):
            def __init__(self):
                self.added = []
                self.created = []

            def api_music(self, path):
                return super().api_music(path)

            def paginated(self, path, extract, fresh=False):
                if "/albums/" in path and "/tracks" in path:
                    # the new album's catalog tracks (song-row shaped)
                    aid = path.split("/albums/")[1].split("/")[0]
                    return [{"id": f"9{aid}00", "catalog_id": f"9{aid}00",
                             "type": "songs"}]
                return super().paginated(path, extract, fresh=fresh)

            def find_library_playlist(self, name):
                return None

            def playlist_create(self, name, description=""):
                self.created.append(name)
                return "p.new"

            def playlist_add_tracks(self, pid, catalog_ids):
                self.added.append((pid, catalog_ids))
                return 200

        mk = AddMk()
        watcher = ReleaseWatcher(store, FakeBrowser({}), mk,
                                 emit_fn=lambda t, d: events.append((t, d)),
                                 interval=3600)
        with unittest.mock.patch.object(cfg.config, "watcher_auto_playlist",
                                        "New Music (auto)"), \
                unittest.mock.patch.object(cfg.config, "enable_writes",
                                           enable_writes):
            watcher.run_pass()
            # new release on the next pass
            new_album = {"id": "1888",
                         "attributes": {"name": "New LP",
                                        "releaseDate": "2026-06-01"}}
            CATALOG_ALBUMS["1470"].insert(0, new_album)
            try:
                summary = watcher.run_pass()
            finally:
                CATALOG_ALBUMS["1470"].remove(new_album)
        return mk, summary, events

    def test_auto_add_appends_and_reports_the_playlist(self):
        import unittest.mock
        mk, summary, events = self._with_auto_add(enable_writes=True)
        self.assertEqual(summary["auto_added"], 1)
        self.assertEqual(mk.created, ["New Music (auto)"])
        pid, ids = mk.added[0]
        self.assertEqual(pid, "p.new")
        self.assertTrue(ids and all(i.isdigit() for i in ids),
                        "auto-add posts CATALOG song ids")
        self.assertEqual(events[-1][0], "release.found")
        self.assertEqual(events[-1][1]["auto_added_to"], "p.new")

    def test_auto_add_without_writes_is_reported_not_attempted(self):
        mk, summary, events = self._with_auto_add(enable_writes=False)
        self.assertEqual(mk.added, [], "writes off = no Apple mutation")
        self.assertIn("auto_add_skipped", events[-1][1])


class TestDiscipline(unittest.TestCase):
    """#176: restarts must not stampede the rate budget; passes must end
    even when Apple 429s every lookup."""

    def test_fresh_boot_pass_is_skipped(self):
        store = FakeStore()
        watcher = make_watcher(store=store, interval=86400)
        # a pass completed 5 minutes ago — inside half the daily interval
        store.set_cursor("watcher.pass", {"completed_at": time.time() - 300})
        self.assertTrue(watcher._boot_pass_fresh())
        # 12 hours old — half of 86400 — stale enough to run
        store.set_cursor("watcher.pass", {"completed_at": time.time() - 43200})
        self.assertFalse(watcher._boot_pass_fresh())
        # no pass ever — nothing to skip
        self.assertFalse(make_watcher(store=FakeStore(),
                                      interval=86400)._boot_pass_fresh())

    def test_pass_stops_at_the_time_budget(self):
        calls = []

        def slow_check(art, summary):
            calls.append(1)
            time.sleep(0.05)
            return True

        watcher = make_watcher()
        watcher._check_artist = slow_check
        watcher.time_budget_s = 0.09
        summary = watcher.run_pass()
        self.assertTrue(summary.get("time_budget_exhausted"),
                        "the wall-clock budget ends the pass")
        self.assertLess(len(calls), len(ARTISTS),
                        "fewer artists than the whole list ran")


if __name__ == "__main__":
    unittest.main(verbosity=2)
