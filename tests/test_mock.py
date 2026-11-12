"""Mock mode tests (v0.4 #33 #80 #83) — hermetic.

Run:  python3 -m unittest discover -s tests

The mock doubles as a schema-conformance harness (#83): every fixture, run
through the REAL mk normalizers (pure functions), must validate against the
response models. If a fixture rots out of the model shape, CI fails.
"""
import os
import sys
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ampd.mock import MockKit, BrowserErrorMock
from ampd.musickit import item_row, song_row  # real, pure
from ampd import models as M


def route_library_list(raw_page, offset=0):
    """The exact transformation routes/library.py list_resource does."""
    items = [item_row(t) for t in raw_page.get("data", [])]
    return {"items": items, "count": len(items),
            "next_offset": offset + len(items) if raw_page.get("next") else None}


class TestModelConformance(unittest.TestCase):
    """#83 — every fixture validates against the response models."""

    def setUp(self):
        self.mock = MockKit()

    def test_every_library_song_fits_item_row(self):
        for raw in self.mock.songs:
            row = item_row(raw)
            model = M.ItemRow.model_validate(row)
            self.assertEqual(model.name, raw["attributes"]["name"])
            # raw attributes blob passes through untouched (extra=allow)
            self.assertEqual(model.attributes["name"],
                             raw["attributes"]["name"])

    def test_every_album_artist_playlist_fits(self):
        for raw in self.mock.albums + self.mock.artists + self.mock.playlists:
            row = item_row(raw)
            M.ItemRow.model_validate(row)

    def test_library_list_page_fits(self):
        page = route_library_list(
            self.mock.api_music("/v1/me/library/songs?limit=25&offset=0"))
        M.LibraryList.model_validate(page)
        self.assertEqual(page["count"], 25)

    def test_now_playing_fits(self):
        M.NowPlaying.model_validate(self.mock.now_playing())

    def test_queue_fits(self):
        route_shape = {"items": self.mock.queue()}
        M.Queue.model_validate(route_shape)

    def test_search_fits(self):
        out = {}
        data = self.mock.api_music(
            "/v1/me/library/search?term=mock&limit=25")
        for kind, group in data.get("results", {}).items():
            if isinstance(group, dict) and group.get("data"):
                out[kind.replace("library-", "")] = [
                    item_row(t) for t in group["data"]]
        for kind, items in out.items():
            M.ItemList.model_validate({"items": items})
        self.assertTrue(out, "search finds synthetic hits")

    def test_recommendations_fits(self):
        data = self.mock.api_music("/v1/me/recommendations")
        groups = []
        for rec in data.get("data", []):
            attrs = rec.get("attributes", {}) or {}
            rels = rec.get("relationships", {}) or {}
            groups.append({
                "id": rec.get("id"),
                "title": attrs.get("title", {}).get("string")
                         if isinstance(attrs.get("title"), dict)
                         else attrs.get("title"),
                "reason": attrs.get("reason"),
                "items": [item_row(t) for rel in rels.values()
                          for t in rel.get("data", [])]})
        M.Recommendations.model_validate({"groups": groups})
        self.assertTrue(groups)

    def test_lyrics_fixture_parses_and_fits(self):
        from ampd.routes.catalog import _parse_ttml  # pure
        data = self.mock.api_music(
            f"/v1/catalog/us/songs/{self.mock.catalog_songs[0]['id']}/lyrics")
        ttml = (data.get("data") or [{}])[0].get("attributes", {}).get("ttml")
        self.assertTrue(ttml)
        lines = _parse_ttml(ttml)
        M.Lyrics.model_validate({"song_id": "x", "lines": lines})
        self.assertGreater(len(lines), 5)

    def test_snapshot_fits_stream_contract(self):
        snap = self.mock.snapshot()
        for key in ("shuffle", "repeat", "volume", "isPlaying", "queue"):
            self.assertIn(key, snap)
        M.Queue.model_validate({"items": snap["queue"]})


class TestPaginatedWalk(unittest.TestCase):
    def test_next_links_chain_to_the_end(self):
        # install the mock into the REAL musickit surface (like AMPD_MOCK=1
        # does), walk with the real-shape paginated equivalent, restore.
        # NEVER call the real browser-driving paginated from tests.
        import ampd.musickit as mk
        from ampd.mock import install
        saved = {k: getattr(mk, k) for k in
                 ("api_music", "paginated", "raw_api")}
        try:
            mock = install(mk)
            rows = mk.paginated(
                "/v1/me/library/songs?limit=100",
                lambda d: [item_row(t) for t in d.get("data", [])])
            self.assertEqual(rows and len(rows), len(mock.songs),
                             "absolute next-links must walk every page")
        finally:
            for k, v in saved.items():
                setattr(mk, k, v)


class TestMockState(unittest.TestCase):
    """The mock is a world that behaves — writes mutate it."""

    def setUp(self):
        self.mock = MockKit()

    def test_ratings_roundtrip(self):
        cid = self.mock.catalog_songs[0]["id"]
        self.mock.raw_api(f"/v1/me/ratings/songs/{cid}", method="PUT")
        self.assertEqual(self.mock.ratings[cid], 1)
        self.mock.raw_api(f"/v1/me/ratings/songs/{cid}", method="DELETE")
        self.assertEqual(self.mock.ratings[cid], 0)

    def test_favorites_toggle(self):
        cid = next(s["id"] for s in self.mock.catalog_songs
                   if s["id"] not in self.mock.favorites)
        n0 = len(self.mock.favorites)
        self.mock.raw_api(f"/v1/me/favorites?ids[songs]={cid}", method="POST")
        self.assertGreater(len(self.mock.favorites), n0)
        self.mock.raw_api(f"/v1/me/favorites?ids[songs]={cid}",
                          method="DELETE")

    def test_playlist_create_add_rename_delete(self):
        n0 = len(self.mock.playlists)
        pid = self.mock.raw_api("/v1/me/library/playlists", method="POST",
                                body={"attributes": {"name": "CI Test"}})
        self.assertEqual(len(self.mock.playlists), n0 + 1)
        pl = self.mock.playlists[-1]
        self.assertEqual(pl["attributes"]["name"], "CI Test")
        # add a track
        cid = self.mock.catalog_songs[0]["id"]
        self.mock.raw_api(
            f"/v1/me/library/playlists/{pl['id']}/tracks?ids[songs]={cid}",
            method="POST")
        self.assertEqual(len(pl["relationships"]["tracks"]["data"]), 1)
        # rename
        self.mock.raw_api(f"/v1/me/library/playlists/{pl['id']}",
                          method="PATCH",
                          body={"attributes": {"name": "Renamed"}})
        self.assertEqual(pl["attributes"]["name"], "Renamed")
        # delete -> the documented husk (name=None)
        self.mock.raw_api(f"/v1/me/library/playlists/{pl['id']}",
                          method="DELETE")
        self.assertIsNone(pl["attributes"]["name"])
        self.assertTrue(pl.get("_deleted"))

    def test_queue_reorder_keeps_the_playhead(self):
        """#87: whole-list PUT semantics — the queue becomes EXACTLY the
        sent order and the playhead stays on the SAME track."""
        ids = [t["id"] for t in self.mock.queue()]
        self.assertGreaterEqual(len(ids), 3)
        before = self.mock.snapshot()
        reordered = list(reversed(ids))
        self.mock.queue_reorder(reordered)
        self.assertEqual([t["id"] for t in self.mock.queue()], reordered)
        # the now-playing item is unchanged — same id, new index
        after = self.mock.snapshot()
        self.assertEqual(after["title"], before["title"])
        # a missing id is a loud 404-shape error, never a silent partial
        from ampd.mock import BrowserErrorMock
        with self.assertRaises(BrowserErrorMock):
            self.mock.queue_reorder(reordered + ["9999999"])
        self.assertIsNone(self.mock.find_library_playlist("Renamed"))

    def test_playback_state_machine(self):
        cid = self.mock.catalog_songs[2]["id"]
        self.mock.play_song(cid)
        np = self.mock.now_playing()
        self.assertTrue(np["isPlaying"])
        self.assertEqual(np["title"],
                         self.mock.by_catalog_id[cid]["attributes"]["name"])
        # playhead advances
        e1 = self.mock.now_playing()["elapsedMs"]
        time.sleep(0.05)
        e2 = self.mock.now_playing()["elapsedMs"]
        self.assertGreater(e2, e1, "synthetic playhead moves while playing")
        # pause freezes it
        self.mock.playback_command("pause")
        e3 = self.mock.now_playing()["elapsedMs"]
        time.sleep(0.05)
        self.assertEqual(self.mock.now_playing()["elapsedMs"], e3)
        self.mock.playback_command("next")
        self.mock.playback_command("previous")
        self.mock.playback_command("play")
        with self.assertRaises(BrowserErrorMock):
            self.mock.playback_command("shrimp")

    def test_drain_stream_advances_and_loops(self):
        mock = self.mock
        mock.play_song(mock.catalog_songs[0]["id"])
        first = mock.drain_stream(0)
        self.assertTrue(first, "drain returns buffered events")
        seq = first[-1]["seq"]
        time.sleep(0.02)
        second = mock.drain_stream(seq)
        self.assertTrue(all(e["seq"] > seq for e in second),
                        "only NEW events come back (seq cursor)")

    def test_unknown_path_raises_browser_error(self):
        with self.assertRaises(BrowserErrorMock):
            self.mock.api_music("/v1/me/library/nonexistent")


class TestOverlay(unittest.TestCase):
    """OBS overlay (#94) — serves the stream's last emitted state."""

    def setUp(self):
        from ampd.routes import stream
        self.stream = stream
        self.stream._remember({"isPlaying": True, "title": "Signal 5",
                               "artist": "Mock Artist 2", "album": None,
                               "id": "6400017", "durationMs": 200000,
                               "elapsedMs": 45000, "ts": int(
                                   time.time() * 1000)})

    def tearDown(self):
        self.stream._remember({"isPlaying": False, "title": None,
                               "artist": None, "album": None, "id": None,
                               "durationMs": None, "elapsedMs": None})

    def test_last_snapshot_roundtrip(self):
        snap = self.stream.last_snapshot()
        self.assertEqual(snap["title"], "Signal 5")
        self.assertEqual(snap["artist"], "Mock Artist 2")

    def test_json_payload_is_model_valid(self):
        from ampd.routes.overlay import _payload
        from ampd import models as M
        M.OverlayNowPlaying.model_validate(_payload())

    def test_text_template_substitution(self):
        from ampd.routes.overlay import now_playing_txt
        out = now_playing_txt(format="{title} by {artist} [{elapsed}]")
        self.assertIn("Signal 5", out)
        self.assertIn("Mock Artist 2", out)
        self.assertIn("0:45", out)
        self.assertIsInstance(out, str)

    def test_text_template_empty_values(self):
        from ampd.routes.overlay import now_playing_txt
        self.stream._remember({"isPlaying": False, "title": None,
                               "artist": None, "album": None, "id": None,
                               "durationMs": None, "elapsedMs": None})
        out = now_playing_txt(format="{title} — {artist}")
        self.assertNotIn("None", out, "nulls must render as '', never 'None'")


if __name__ == "__main__":
    unittest.main(verbosity=2)
