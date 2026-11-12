"""Scheduled sweep digest tests (v0.6) — hermetic.

`build_digest` is one library walk feeding BOTH reports (never two walks);
the scheduler is stall-gated and never raises.
"""
import os
import sys
import unittest
import unittest.mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tonearm.digest import DigestScheduler
from tonearm import sweeps


def song(n, catalog=None, plays=0):
    attrs = {"name": f"Song {n}", "artistName": "Artist", "albumName": "Album",
             "durationInMillis": 1000}
    if plays is not None:
        attrs["playCount"] = plays
    return {"id": catalog or f"i.{n}", "type": "library-songs",
            "attributes": attrs}


ROWS = [song(1, catalog="c.1", plays=5),
        song(1, catalog="c.1", plays=5),      # duplicate of the first
        song(2, catalog="c.2", plays=0),
        song(3, catalog="c.3")]               # playCount absent


class TestBuildDigest(unittest.TestCase):
    def test_one_walk_feeds_both_reports(self):
        calls = []

        def walk():
            calls.append(1)
            return ROWS

        with unittest.mock.patch.object(sweeps, "all_library_songs", walk):
            d = sweeps.build_digest()
        self.assertEqual(len(calls), 1, "dedupe + never-played share one walk")
        self.assertEqual(d["library_size"], 4)
        self.assertEqual(d["duplicate_groups"], 1)
        self.assertEqual(d["removable_rows"], 1)
        self.assertEqual(d["never_played"], 2)
        self.assertTrue(d["play_count_available"])
        self.assertEqual(len(d["sample_duplicates"]), 1)
        self.assertLessEqual(len(d["sample_never_played"]), 10)

    def test_absent_play_counts_are_reported_honestly(self):
        with unittest.mock.patch.object(sweeps, "all_library_songs",
                                        lambda: [song(1, plays=None)]):
            d = sweeps.build_digest()
        self.assertFalse(d["play_count_available"],
                         "no play-count data is not the same as 'unplayed'")


class FakeBrowser:
    def __init__(self, health):
        self._health = health

    def health(self):
        return self._health


class TestScheduler(unittest.TestCase):
    def test_run_once_emits_the_digest_event(self):
        seen = []

        sched = DigestScheduler(FakeBrowser({}), interval=3600,
                                build_fn=lambda: {"library_size": 9},
                                emit_fn=lambda t, d: seen.append((t, d)))
        payload = sched.run_once()
        self.assertEqual(payload, {"library_size": 9})
        self.assertEqual(seen, [("sweep.digest", {"library_size": 9})])

    def test_stalled_renderer_skips_the_walk(self):
        sched = DigestScheduler(
            FakeBrowser({"last_ok": False, "consecutive_failures": 2}),
            interval=3600, build_fn=lambda: self.fail("must not walk"),
            emit_fn=lambda t, d: None)
        self.assertTrue(sched._stalled())

    def test_cold_renderer_counts_as_available(self):
        sched = DigestScheduler(
            FakeBrowser({"last_ok": None, "last_ping_ts": None,
                         "consecutive_failures": 0}),
            interval=3600, build_fn=lambda: {}, emit_fn=lambda t, d: None)
        self.assertFalse(sched._stalled(),
                         "background work must be able to trigger the first "
                         "connect — see store._renderer_available")


if __name__ == "__main__":
    unittest.main(verbosity=2)
