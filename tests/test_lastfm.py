"""Last.fm scrobbler tests (v0.5 #97 #98) — hermetic.

The 50%/4-min rule, the dedupe contract, and the event->scrobble decision
layer (with the API POSTs mocked out). No network, no threads.
"""
import os
import sys
import tempfile
import time
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ampd import lastfm
from ampd.lastfm import Scrobbler, qualifies


def ev(seq, key, title="Song", artist="Artist", album="Album",
       playing=True, elapsed=None, duration=None, ts=None):
    e = {"seq": seq, "id": key, "title": title, "artist": artist,
         "album": album, "isPlaying": playing, "ts": ts or time.time() * 1000}
    if elapsed is not None:
        e["elapsedMs"] = elapsed
    if duration is not None:
        e["durationMs"] = duration
    return e


class FakeStore:
    """record_scrobble contract: True once, False on the same key."""
    def __init__(self):
        self.seen = set()
        self.enabled = True

    def record_scrobble(self, track_id, started_at):
        k = (track_id, round(started_at, 3))
        if k in self.seen:
            return False
        self.seen.add(k)
        return True


class TestRule(unittest.TestCase):
    def test_under_half_short_track(self):
        self.assertFalse(qualifies(30_000, 200_000))       # 15% of 3:20

    def test_half_counts(self):
        self.assertTrue(qualifies(100_000, 200_000))       # exactly 50%

    def test_four_minutes_on_a_long_track(self):
        # 10-min track, 45% played = 4:30 -> qualifies on the 4-min arm
        self.assertTrue(qualifies(270_000, 600_000))
        self.assertFalse(qualifies(230_000, 600_000))      # 3:50 on 10-min

    def test_zero_elapsed_never(self):
        self.assertFalse(qualifies(0, 200_000))
        self.assertFalse(qualifies(None, 200_000))


class TestScrobbler(unittest.TestCase):
    def setUp(self):
        self.store = FakeStore()
        self.s = Scrobbler(self.store, {"api_key": "k", "secret": "s",
                                        "sk": "sk", "user": "u"})
        self.posts = []

        def fake_call(params, api_key, secret, sk=None):
            self.posts.append(params)
            return {}

        self.patcher = mock.patch.object(lastfm, "_call", side_effect=fake_call)
        self.patcher.start()
        self.fake_call = fake_call

    def tearDown(self):
        self.patcher.stop()

    def _key(self, method):
        return next(p for p in self.posts if p["method"] == method)

    def test_track_change_with_50pct_scrobbles_with_start_time(self):
        t0 = 1_700_000_000.0
        s = self.s.process_events([
            ev(1, "a", elapsed=1_000, duration=200_000, ts=t0 * 1000),
            ev(2, "a", elapsed=120_000, duration=200_000),   # 60% — fires now
            ev(3, "a", elapsed=130_000, duration=200_000),
        ])
        self.assertEqual(len(s), 1, "qualifies mid-track: the rule is "
                                    "'whichever comes first'")
        sc = self._key("track.scrobble")
        self.assertEqual(sc["track"], "Song")
        self.assertEqual(sc["timestamp"], int(t0), "scrobble timestamp = "
                                                   "when the play STARTED")
        self.assertAlmostEqual(sc["duration"], 200)

    def test_change_before_half_does_not_scrobble(self):
        s = self.s.process_events([
            ev(1, "a", elapsed=1_000, duration=200_000),
            ev(2, "a", elapsed=60_000, duration=200_000),    # 30% then skipped
            ev(3, "b", elapsed=1_000, duration=200_000),
        ])
        self.assertEqual(len(s), 0)
        self.assertFalse([p for p in self.posts
                          if p["method"] == "track.scrobble"])

    def test_dedupe_on_restart_replay(self):
        t0 = 1_700_000_000.0
        self.s.process_events([
            ev(1, "a", elapsed=1_000, duration=100_000, ts=t0 * 1000),
            ev(2, "a", elapsed=90_000, duration=100_000, ts=t0 * 1000),
        ])
        base = len([p for p in self.posts
                    if p["method"] == "track.scrobble"])
        # a restart replays the SAME buffer (same ts — that's what a replay
        # is); a fresh scrobbler must not re-submit the already-scrobbled play
        replay = Scrobbler(self.store, self.s.creds)
        with mock.patch.object(lastfm, "_call", side_effect=self.fake_call):
            got = replay.process_events([
                ev(1, "a", elapsed=95_000, duration=100_000, ts=t0 * 1000),
            ])
        self.assertEqual(got, [], "the replayed play was already scrobbled — "
                                  "the (id, started_at) marker blocks it")
        self.assertEqual(len([p for p in self.posts
                              if p["method"] == "track.scrobble"]), base,
                         "no second API call for the same play")
        # and the dedupe must not wedge the scrobbler: the NEXT play flows
        with mock.patch.object(lastfm, "_call", side_effect=self.fake_call):
            got = replay.process_events([
                ev(3, "b", elapsed=1_000, duration=100_000, ts=t0 * 1000),
                ev(4, "b", elapsed=60_000, duration=100_000, ts=t0 * 1000),
            ])
        self.assertEqual([k for k, _ in got], ["b"],
                         "the next genuinely-new play scrobbles normally")

    def test_now_playing_once_per_track(self):
        self.s.process_events([
            ev(1, "a", elapsed=1_000, duration=200_000),
            ev(2, "a", elapsed=5_000, duration=200_000),
            ev(3, "a", elapsed=9_000, duration=200_000),
        ])
        nps = [p for p in self.posts
               if p["method"] == "track.updateNowPlaying"]
        self.assertEqual(len(nps), 1, "one submit per track key")

    def test_pause_does_not_scrobble_half_heard(self):
        self.s.process_events([
            ev(1, "a", elapsed=1_000, duration=200_000),
            ev(2, "a", elapsed=90_000, duration=200_000, playing=False),
        ])
        self.assertEqual([p for p in self.posts
                          if p["method"] == "track.scrobble"], [],
                         "paused mid-track: no scrobble until it actually "
                         "qualifies while playing")


class TestCreds(unittest.TestCase):
    def test_creds_file_is_0600(self):
        with mock.patch.object(lastfm.config, "lastfm_creds_path",
                               return_value=os.path.join(
                                   tempfile.mkdtemp(), "lf.json")):
            p = lastfm._save_creds({"api_key": "k", "secret": "s",
                                    "sk": "sk", "user": "u"})
            mode = os.stat(p).st_mode & 0o777
            self.assertEqual(mode, 0o600)
            self.assertEqual(lastfm.load_creds()["user"], "u")


if __name__ == "__main__":
    unittest.main(verbosity=2)
