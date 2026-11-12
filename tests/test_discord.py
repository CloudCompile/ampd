"""Discord Rich Presence bridge tests (v0.5 #96) — hermetic.

Covers the pure mapping layer + the opt-in gating. The IPC socket dance is
exercised only when a local Discord client exists (never in CI).
"""
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ampd import discord


class TestPresenceMapping(unittest.TestCase):
    def test_playing_maps_to_activity(self):
        act = discord._activity_from({
            "isPlaying": True, "title": "Signal 5", "artist": "Mock Artist 2",
            "album": "Plastic Fields", "durationMs": 200000,
            "elapsedMs": 50000})
        self.assertEqual(act["details"], "Signal 5")
        self.assertEqual(act["state"], "Mock Artist 2")
        # end timestamp ≈ now + (duration - elapsed) = +150s (1s tolerance)
        end = act["timestamps"]["end"]
        import time
        self.assertAlmostEqual(end - time.time(), 150, delta=2)

    def test_paused_clears(self):
        self.assertIsNone(discord._activity_from({
            "isPlaying": False, "title": "Signal 5", "artist": "x",
            "durationMs": 200000, "elapsedMs": 50000}))

    def test_no_title_clears(self):
        self.assertIsNone(discord._activity_from({
            "isPlaying": True, "title": None, "artist": "x"}))

    def test_no_progress_still_an_activity(self):
        act = discord._activity_from({
            "isPlaying": True, "title": "Song", "artist": "A",
            "durationMs": None, "elapsedMs": None})
        self.assertEqual(act["details"], "Song")
        self.assertNotIn("timestamps", act, "no playhead -> no fake countdown")


class TestOptInGating(unittest.TestCase):
    def test_off_by_default(self):
        with mock.patch("ampd.config.config") as c:
            c.discord_enabled = False
            c.mock_enabled = False
            with mock.patch("threading.Thread") as th:
                discord.start()
                th.assert_not_called()

    def test_skipped_in_mock_mode(self):
        with mock.patch("ampd.config.config") as c:
            c.discord_enabled = True
            c.mock_enabled = True
            c.discord_client_id = "x"
            with mock.patch("threading.Thread") as th:
                discord.start()
                th.assert_not_called()

    def test_requires_client_id(self):
        with mock.patch("ampd.config.config") as c:
            c.discord_enabled = True
            c.mock_enabled = False
            c.discord_client_id = ""
            with mock.patch("threading.Thread") as th:
                discord.start()
                th.assert_not_called()


if __name__ == "__main__":
    unittest.main(verbosity=2)
