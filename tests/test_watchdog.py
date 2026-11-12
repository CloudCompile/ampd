"""Unit tests for the renderer watchdog state machine (no Chrome, no network).

The watchdog logic lives in Browser._watchdog_tick / _wd_set; we exercise it
against a fake socket by stubbing the CDP layer. The real loop thread is
never started here (it waits for a connect that never comes in CI).
"""
import os
import sys
import threading
import time
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tonearm.browser import Browser, BrowserError
from tonearm.config import config


class WatchdogTestBase(unittest.TestCase):
    def setUp(self):
        self.b = Browser.__new__(Browser)      # skip __init__ (thread start)
        self.b._lock = threading.RLock()
        self.b._ws = object()                  # pretend a socket exists
        self.b._n = 0
        self.b._watchdog_armed = threading.Event()
        self.b._watchdog_armed.set()
        self.b._wd_lock = threading.Lock()
        self.b._wd = {"running": False, "last_ping_ts": None, "last_ok": None,
                      "consecutive_failures": 0, "recycles": 0,
                      "last_action": ""}
        self._tries = config.watchdog_tries
        config.watchdog_tries = 3
        # default: the CDP ping answers (hermetic); tests flip side_effect
        self._raw = mock.patch.object(self.b, "_raw_call", return_value={})
        self._raw_mock = self._raw.start()
        self.addCleanup(self._raw.stop)

    def tearDown(self):
        config.watchdog_tries = self._tries


class TestTick(WatchdogTestBase):
    def test_ok_ping_resets(self):
        for _ in range(2):
            self.b._watchdog_tick()
        h = self.b.health()
        self.assertTrue(h["last_ok"])
        self.assertEqual(h["consecutive_failures"], 0)
        self.assertEqual(h["last_action"], "ping ok")

    def test_busy_lock_is_skipped_not_counted(self):
        # RLock is reentrant on the SAME thread, so contention must come
        # from another thread — like a real in-flight request.
        held, release = threading.Event(), threading.Event()
        def hold():
            with self.b._lock:
                held.set()
                release.wait(2)
        t = threading.Thread(target=hold)
        t.start()
        held.wait(2)
        try:
            self.b._watchdog_tick()
        finally:
            release.set()
            t.join(2)
        h = self.b.health()
        self.assertIn("skipped", h["last_action"])
        self.assertEqual(h["consecutive_failures"], 0)

    def test_stalls_count_then_recycle_at_tries(self):
        """1-2 failed pings = recoverable stall; the 3rd recycles. Matches the
        ~60s renderer-stall window Apple's page is known to ride out."""
        self._raw_mock.side_effect = BrowserError("stalled")
        with mock.patch.object(self.b, "_close_ws") as cw, \
             mock.patch.object(self.b, "_connect") as cn:
            self.b._watchdog_tick()            # stall 1
            h = self.b.health()
            self.assertFalse(cw.called, "must NOT recycle on first failure")
            self.assertEqual(h["consecutive_failures"], 1)
            self.b._watchdog_tick()            # stall 2
            self.assertFalse(cw.called, "must NOT recycle on second failure")
            self.b._watchdog_tick()            # stall 3 -> dead
            self.assertTrue(cw.called and cn.called, "recycle at tries")
        h = self.b.health()
        self.assertEqual(h["recycles"], 1)
        self.assertEqual(h["consecutive_failures"], 0)

    def test_recovery_between_failures_cancels_recycle(self):
        """A stall that recovers (the documented ~60s behavior) must not
        accumulate toward a recycle."""
        self._raw_mock.side_effect = BrowserError("stalled")
        self.b._watchdog_tick()
        self.b._watchdog_tick()
        self._raw_mock.side_effect = None      # renderer recovered on its own
        self.b._watchdog_tick()
        self.assertEqual(self.b.health()["consecutive_failures"], 0)

    def test_socket_down_hot_recovers(self):
        """Post-failure the socket is None; the watchdog reconnects so the
        NEXT call succeeds instead of cold-starting."""
        self.b._ws = None
        with mock.patch.object(self.b, "_connect") as cn:
            self.b._watchdog_tick()
            self.assertTrue(cn.called)
        h = self.b.health()
        self.assertTrue(h["last_ok"])
        self.assertIn("reconnected", h["last_action"])

    def test_reconnect_failure_is_counted(self):
        self.b._ws = None
        with mock.patch.object(self.b, "_connect",
                               side_effect=BrowserError("chrome is gone")):
            self.b._watchdog_tick()
        h = self.b.health()
        self.assertFalse(h["last_ok"])
        self.assertEqual(h["consecutive_failures"], 1)

    def test_disarmed_browser_never_counts(self):
        self.b._watchdog_armed.clear()
        self.b._wd_set(ok="ping ok")
        self.assertFalse(self.b.health()["running"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
