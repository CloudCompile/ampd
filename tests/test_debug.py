"""Unit tests for the /api/debug building blocks.

The rule under test: the debug surface must never eval the renderer. The
ring buffer is filled as a side effect of real calls; tab_url uses the
socket-free Chrome HTTP API.
"""
import os
import sys
import threading
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tonearm.browser import Browser, BrowserError


def bare_browser():
    b = Browser.__new__(Browser)          # no thread start
    b._lock = threading.RLock()
    b._ws = None
    b._n = 0
    b._target_id = None
    b._watchdog_armed = threading.Event()
    b._wd_lock = threading.Lock()
    b._wd = {"running": False, "last_ping_ts": None, "last_ok": None,
             "consecutive_failures": 0, "recycles": 0, "last_action": ""}
    b._recent_lock = threading.Lock()
    from collections import deque
    b._recent = deque(maxlen=50)
    return b


class TestRingBuffer(unittest.TestCase):
    def test_records_success_and_failure(self):
        b = bare_browser()
        with mock.patch.object(b, "_raw_call_inner", return_value={}):
            b._raw_call("Runtime.evaluate", expression="(() => 1+1)()",
                        returnByValue=True, deadline_s=5)
        self.assertEqual(len(b.recent_calls()), 1)
        entry = b.recent_calls()[0]
        self.assertTrue(entry["ok"])
        self.assertIn("1+1", entry["what"])
        self.assertIn("ms", entry)

        with mock.patch.object(b, "_raw_call_inner",
                               side_effect=BrowserError("timed out")):
            with self.assertRaises(BrowserError):
                b._raw_call("Runtime.evaluate", expression="boom()", deadline_s=1)
        recent = b.recent_calls()
        self.assertEqual(len(recent), 2)
        self.assertFalse(recent[1]["ok"])
        self.assertIn("timed out", recent[1]["error"])

    def test_truncates_long_expressions(self):
        b = bare_browser()
        with mock.patch.object(b, "_raw_call_inner", return_value={}):
            b._raw_call("Runtime.evaluate", expression="x" * 500, deadline_s=5)
        self.assertLessEqual(len(b.recent_calls()[0]["what"]), 120)

    def test_ring_is_bounded(self):
        b = bare_browser()
        with mock.patch.object(b, "_raw_call_inner", return_value={}):
            for i in range(80):
                b._raw_call("Runtime.evaluate", expression=f"e{i}()", deadline_s=5)
        self.assertEqual(len(b.recent_calls()), 50, "must stay a 50 ring")
        self.assertEqual(b.recent_calls()[0]["what"], "e30()",
                         "oldest evicted")

    def test_recording_never_breaks_a_call(self):
        """If diagnostics blow up, the real call must still succeed — the
        guard lives inside _record_call itself."""
        b2 = bare_browser()
        b2._recent = mock.MagicMock()          # deque -> failing mock
        b2._recent.append.side_effect = RuntimeError("nope")
        with mock.patch.object(b2, "_raw_call_inner", return_value={"ok": 1}):
            self.assertEqual(b2._raw_call("Runtime.evaluate",
                                          expression="q()", deadline_s=5),
                             {"ok": 1},
                             "call must succeed even when recording fails")


class TestTabUrl(unittest.TestCase):
    def test_socket_free_lookup(self):
        b = bare_browser()
        payload = b'[{"type":"page","url":"https://music.apple.com/us/listen-now"}]'
        with mock.patch("urllib.request.urlopen",
                        mock.mock_open(read_data=payload)):
            self.assertEqual(b.tab_url(), "https://music.apple.com/us/listen-now")

    def test_degrades_to_none(self):
        b = bare_browser()
        with mock.patch("urllib.request.urlopen",
                        side_effect=OSError("chrome gone")):
            self.assertIsNone(b.tab_url(),
                              "debug surface must degrade, never raise")


class TestDebugPayload(unittest.TestCase):
    def test_assembly(self):
        from tonearm.routes import debug as dbg
        b = bare_browser()
        with mock.patch.object(dbg, "browser", b):
            out = dbg.debug()
        self.assertIn("tab_url", out)
        self.assertIn("renderer", out)
        self.assertIn("recent_calls", out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
