"""Audio pipeline tests (v0.5 #92 #93 #95) — hermetic.

No pulse, no ffmpeg, no subprocesses: these cover the pure decision layers
(format recipes, bitrate validation, join-playhead state, loudnorm filter
args). The subprocess plumbing itself is exercised only on a real box with
TONEARM_AUDIO=1 (or the Docker image).
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tonearm.audio import FORMATS, BITRATE_RE, Pipeline, join_playhead, \
    note_playhead


class TestFormats(unittest.TestCase):
    def test_three_formats_with_browser_safe_types(self):
        self.assertEqual(set(FORMATS), {"mp3", "ogg", "opus"})
        self.assertEqual(FORMATS["mp3"]["type"], "audio/mpeg")
        for f in ("ogg", "opus"):
            self.assertEqual(FORMATS[f]["type"], "audio/ogg")
        # opus rejects 44.1 kHz — the recipe must pin 48
        self.assertEqual(FORMATS["opus"]["rate"], 48000)

    def test_codec_args_per_format(self):
        mp3 = Pipeline("mp3", "160k", False)
        self.assertIn("libmp3lame", mp3._ffmpeg_tail())
        self.assertIn("-f mp3", mp3._ffmpeg_tail())
        opus = Pipeline("opus", "96k", False)
        self.assertIn("libopus", opus._ffmpeg_tail())
        self.assertIn("-f ogg", opus._ffmpeg_tail())
        self.assertIn("-ar 48000", opus._ffmpeg_tail())

    def test_loudnorm_filter_toggle(self):
        plain = Pipeline("mp3", "160k", False)
        normed = Pipeline("mp3", "160k", True)
        self.assertNotIn("loudnorm", " ".join(plain._filter_args()))
        self.assertIn("loudnorm=I=-16", " ".join(normed._filter_args()))
        self.assertEqual(plain.key, ("mp3", "160k", False))
        self.assertEqual(normed.key, ("mp3", "160k", True))


class TestBitrateValidation(unittest.TestCase):
    def test_valid_bitrates(self):
        for b in ("96k", "160k", "320k", "128", "64k"):
            self.assertTrue(BITRATE_RE.match(b), b)

    def test_invalid_bitrates(self):
        for b in ("", "k", "160kk", "abc", "1000000k", "-160k", "1.6k"):
            self.assertFalse(BITRATE_RE.match(b), b)


class TestJoinPlayhead(unittest.TestCase):
    def test_fed_by_stream_state(self):
        note_playhead(45000, True)
        ms, stale = join_playhead()
        self.assertEqual(ms, 45000)
        self.assertFalse(stale)

    def test_stale_when_the_stream_went_quiet(self):
        note_playhead(45000, True)
        # rewind the timestamp — the join must declare staleness loudly
        import tonearm.audio as A
        import time
        with A._playhead_lock:
            A._playhead["ts"] = time.time() - 60
        ms, stale = join_playhead()
        self.assertEqual(ms, 45000, "value kept, staleness flagged")
        self.assertTrue(stale)

    def test_never_played_is_none_not_zero(self):
        import tonearm.audio as A
        with A._playhead_lock:
            A._playhead.update(elapsed_ms=None, ts=0)
        ms, _ = join_playhead()
        self.assertIsNone(ms, "no state must be None — not a fake 0:00")


if __name__ == "__main__":
    unittest.main(verbosity=2)
