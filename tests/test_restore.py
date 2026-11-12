"""Unit tests for the restore planner/executor (v0.3 #24) — hermetic.

Run:  python3 -m unittest discover -s tests
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ampd.restore import build_plan, execute_plan


def export(pls):
    return {"playlists": [
        {"name": n, "tracks": t} for n, t in pls]}


def row(name, artist, catalog_id=None):
    return {"name": name, "artist": artist, "catalog_id": catalog_id}


class TestPlan(unittest.TestCase):
    def test_exists_vs_create(self):
        exp = export([("Favorites", []), ("New One", [])])
        plan = build_plan(exp, lambda n: "p.1" if n.lower() == "favorites" else None,
                          lambda n, a: None)
        modes = {p["name"]: p["mode"] for p in plan["playlists"]}
        self.assertEqual(modes, {"Favorites": "exists", "New One": "create"})
        self.assertEqual(plan["totals"]["exists"], 1)
        self.assertEqual(plan["totals"]["create"], 1)

    def test_catalog_rows_go_direct(self):
        exp = export([("P", [row("Song", "Artist", catalog_id="1440")])])
        plan = build_plan(exp, lambda n: None, lambda n, a: None)
        p = plan["playlists"][0]
        self.assertEqual(p["actions"][0]["kind"], "catalog")
        self.assertEqual(plan["totals"]["catalog"], 1)
        self.assertEqual(plan["totals"]["unmatched"], 0)

    def test_name_fallback_and_never_silent_misses(self):
        exp = export([("P", [row("Found", "A"),
                             row("Lost", "B")])])
        plan = build_plan(exp, lambda n: None,
                          lambda n, a: "999" if n == "Found" else None)
        p = plan["playlists"][0]
        self.assertEqual(p["actions"][0]["kind"], "name-match")
        self.assertEqual(plan["totals"]["name_match"], 1)
        self.assertEqual(len(p["unmatched"]), 1,
                         "unmatched rows are listed with a reason, "
                         "never dropped silently")
        self.assertEqual(p["unmatched"][0]["name"], "Lost")
        self.assertIn("reason", p["unmatched"][0])

    def test_match_budget_bounds_searches(self):
        exp = export([("P", [row(f"S{i}", "A") for i in range(5)])])
        calls = []

        def lookup(n, a):
            calls.append(n)
            return None
        build_plan(exp, lambda n: None, lookup, match_budget=2)
        self.assertEqual(len(calls), 2, "search budget is bounded")

    def test_playlist_without_name_never_crashes(self):
        exp = {"playlists": [{"name": None, "tracks": []}]}
        plan = build_plan(exp, lambda n: None, lambda n, a: None)
        self.assertEqual(plan["playlists"][0]["name"], "")


class FakeMK:
    """Mimics the mk surface execute_plan touches."""

    def __init__(self, existing=None, tracks_after=None):
        self.created = []
        self.added = {}            # pid -> list of batches
        self.existing = existing or {}
        self.tracks_after = tracks_after or {}

    def playlist_create(self, name):
        pid = f"p.new{len(self.created)}"
        self.created.append((name, pid))
        return pid

    def playlist_add_tracks(self, pid, cids):
        self.added.setdefault(pid, []).append(cids)
        return 200

    def playlist_tracks(self, pid, fresh=False):
        return self.tracks_after.get(pid, [])


class TestExecute(unittest.TestCase):
    def _plan(self, mode, tracks=1):
        actions = [{"kind": "catalog", "catalog_id": f"1{i}",
                    "name": f"s{i}", "artist": "a"} for i in range(tracks)]
        return {"totals": {}, "playlists": [
            {"name": "P", "mode": mode,
             "playlist_id": "p.existing" if mode == "exists" else None,
             "track_count": tracks, "actions": actions, "unmatched": []}]}

    def test_creates_and_adds_and_verifies(self):
        fmk = FakeMK(tracks_after={"p.new0": [1, 2]})
        report = execute_plan(self._plan("create", tracks=2), fmk,
                              verify_retries=1, verify_delay=0)
        self.assertEqual(fmk.created, [("P", "p.new0")])
        self.assertEqual(sum(len(b) for b in fmk.added["p.new0"]), 2)
        self.assertEqual(report["verified"][0]["playlist_id"], "p.new0")
        self.assertEqual(report["mismatch"], [])
        self.assertEqual(report["errors"], [])

    def test_exists_mode_reuses_id(self):
        fmk = FakeMK(tracks_after={"p.existing": [1]})
        report = execute_plan(self._plan("exists"), fmk,
                              verify_retries=1, verify_delay=0)
        self.assertEqual(fmk.created, [], "existing playlist is not recreated")
        self.assertEqual(report["verified"][0]["playlist_id"], "p.existing")

    def test_verify_failure_is_reported_not_raised(self):
        fmk = FakeMK()                      # tracks_after empty — count lies
        report = execute_plan(self._plan("exists"), fmk,
                              verify_retries=1, verify_delay=0)
        self.assertEqual(report["verified"], [])
        self.assertEqual(len(report["mismatch"]), 1)
        self.assertIn("async", report["mismatch"][0]["note"])

    def test_per_playlist_errors_continue(self):
        class BoomMK(FakeMK):
            def playlist_add_tracks(self, pid, cids):
                raise RuntimeError("apple hiccup")
        report = execute_plan(self._plan("create"), BoomMK(),
                              verify_retries=1, verify_delay=0)
        self.assertEqual(len(report["errors"]), 1)
        self.assertIn("apple hiccup", report["errors"][0]["error"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
