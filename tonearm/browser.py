"""Chrome DevTools Protocol driver.

Keeps ONE persistent tab on music.apple.com and evaluates JavaScript in it.
Lessons learned the hard way, encoded here:
  * every eval is wrapped in an IIFE — Chrome persists top-level const/let
    between Runtime.evaluate calls, and a redeclaration kills the page context
  * tabs are reused, never spawned per call (tab leaks zombie the browser)
  * the websocket gets a generous read timeout but a tiny close timeout,
    so shutdown can never hang
"""
import json
import logging
import os
import subprocess
import threading
import time
import urllib.request
from collections import deque

import websocket

from .config import config
from .metrics import METRICS

log = logging.getLogger("tonearm.browser")

MUSIC_URL = "https://music.apple.com/"

# dead-simple liveness probe for the renderer (bounded by deadline_s)
PING_JS = "(() => 1 + 1)()"


class BrowserError(RuntimeError):
    pass


class Browser:
    """Owns the single Music tab. All methods are thread-safe."""

    def __init__(self):
        self._lock = threading.RLock()
        self._ws = None
        self._target_id = None
        self._n = 0
        # last-N CDP calls for /api/debug — plain deque, guarded by its own
        # lock, written in _raw_call (try/except: recording must never be
        # able to break a request)
        self._recent = deque(maxlen=50)
        self._recent_lock = threading.Lock()
        # --- renderer watchdog state (flat dict, guarded by its own lock) ---
        # the thread starts at import but WAITS for the first successful
        # connect — importing this module must never touch Chrome (CI has
        # none). Set config.watchdog=0 to never arm it.
        self._watchdog_armed = threading.Event()
        self._wd_lock = threading.Lock()
        self._wd = {"running": False, "last_ping_ts": None, "last_ok": None,
                    "consecutive_failures": 0, "recycles": 0,
                    "last_action": "armed, waiting for first connect"}
        if config.watchdog and not config.mock_enabled:
            # mock mode never drives Chrome — nothing to watchdog
            threading.Thread(target=self._watchdog_loop, daemon=True,
                             name="tonearm-watchdog").start()

    def health(self):
        """Watchdog snapshot — surfaced in /health."""
        with self._wd_lock:
            return dict(self._wd)

    def _wd_set(self, *, ok=None, action=None, recycle=False, fail=None):
        with self._wd_lock:
            self._wd["running"] = self._watchdog_armed.is_set()
            self._wd["last_ping_ts"] = time.time()
            if fail is not None:
                self._wd["consecutive_failures"] += 1
                self._wd["last_ok"] = False
                self._wd["last_action"] = fail
            if ok is not None:
                self._wd["consecutive_failures"] = 0
                self._wd["last_ok"] = True
                self._wd["last_action"] = ok
            if recycle:
                self._wd["recycles"] += 1
                self._wd["consecutive_failures"] = 0
                self._wd["last_action"] = action

    # ------------------------------------------------------------- lifecycle

    def _ensure_chrome(self):
        """Make sure a debuggable Chrome exists; launch one if allowed."""
        try:
            urllib.request.urlopen(config.cdp_url + "/json/version", timeout=2)
            return
        except Exception:
            pass
        if not config.auto_chrome:
            raise BrowserError(
                f"No Chrome with a debug port at {config.cdp_url}. "
                "Start one or set TONEARM_AUTO_CHROME=1.")
        cmd = [
            config.chrome_bin,
            f"--user-data-dir={config.profile_dir}",
            "--remote-debugging-port=" + config.cdp_url.rsplit(":", 1)[-1],
            "--no-sandbox", "--disable-gpu", "--no-first-run",
            "--no-default-browser-check", "--window-size=1400,2200",
        ]
        env = None
        if config.audio_enabled:
            # audible mode: chrome runs on a virtual display and its audio
            # goes to a private pulse sink that the capture pipeline listens
            # to. Headless chrome has no audio output, so this is required
            # for /api/audio/stream.mp3.
            from .audio import broadcaster
            broadcaster.ensure_display(config.audio_display)
            broadcaster.ensure_sink(config.audio_sink)
            env = {
                **os.environ,                      # merge — a bare {DISPLAY,
                "DISPLAY": config.audio_display,   # PULSE_SINK} env strips PATH
                "PULSE_SINK": config.audio_sink,   # and XDG_RUNTIME_DIR, leaving
            }                                      # chrome unable to find pulse
            cmd.append("--autoplay-policy=no-user-gesture-required")
        else:
            if config.headless:
                cmd.append("--headless=new")
        cmd.append("about:blank")
        log.info("launching chrome: %s (audio=%s)", " ".join(cmd), config.audio_enabled)
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         start_new_session=True, env=env or None)
        for _ in range(40):
            time.sleep(0.5)
            try:
                urllib.request.urlopen(config.cdp_url + "/json/version", timeout=2)
                return
            except Exception:
                continue
        raise BrowserError("Chrome did not come up with a debug port")

    READY_JS = """(() => {
      try {
        const inst = window.MusicKit && MusicKit.getInstance();
        if (!inst) return {ready: false};
        return {ready: !!inst.musicUserToken, authorized: !!inst.musicUserToken};
      } catch (e) { return {ready: false}; }
    })()"""

    def _connect(self):
        """Attach to (creating if needed) the persistent music tab.
        Must NEVER call self.call()/self.eval()/wait_ready() — a reconnect
        inside a reconnect recurses under the RLock (py-spy caught it: one
        zombie tab starved every worker thread, even /health hung). Raw
        calls only, everything bounded."""
        self._ensure_chrome()
        tabs = json.loads(urllib.request.urlopen(config.cdp_url + "/json/list", timeout=5).read())
        target = next((t for t in tabs
                       if t.get("type") == "page" and "music.apple.com" in t.get("url", "")), None)
        if target is None:
            req = urllib.request.Request(config.cdp_url + "/json/new?about:blank", method="PUT")
            urllib.request.urlopen(req, timeout=5)
            time.sleep(0.5)
            tabs = json.loads(urllib.request.urlopen(config.cdp_url + "/json/list", timeout=5).read())
            target = next(t for t in tabs if t.get("type") == "page")
        self._target_id = target["id"]
        self._close_ws()                     # never leak the old socket
        self._ws = websocket.create_connection(
            target["webSocketDebuggerUrl"], timeout=60, max_size=100 * 1024 * 1024)
        self._n = 0
        self._raw_call("Page.enable")
        self._raw_call("Runtime.enable")
        # park the tab on Apple Music and wait (bounded) for MusicKit — via
        # _raw_call so a not-ready tab degrades to health=degraded instead
        # of recursing
        if "music.apple.com" not in target.get("url", ""):
            self._raw_call("Page.navigate", url=MUSIC_URL)
            time.sleep(4)
        deadline = time.time() + 30
        while time.time() < deadline:
            try:
                st = self._raw_call("Runtime.evaluate", expression=self.READY_JS,
                                    returnByValue=True)
                if (st.get("result", {}).get("value") or {}).get("ready"):
                    self._watchdog_armed.set()   # first live tab arms the watchdog
                    return
            except BrowserError:
                pass
            time.sleep(1)

    def connect(self):
        with self._lock:
            self._close_ws()
            self._connect()

    def _close_ws(self):
        if self._ws:
            try:
                if self._ws.sock:
                    self._ws.sock.settimeout(3)
                self._ws.close()
            except Exception:
                pass
            self._ws = None

    def close(self):
        with self._lock:
            self._close_ws()

    # ------------------------------------------------------------- low level

    def recent_calls(self):
        """Last-N CDP calls with durations — for /api/debug."""
        with self._recent_lock:
            return list(self._recent)

    def tab_url(self):
        """Current music-tab URL via the debug HTTP API — socket-free (no
        eval, never competes with the renderer it is diagnosing)."""
        try:
            tabs = json.loads(urllib.request.urlopen(
                config.cdp_url + "/json/list", timeout=2).read())
            target = next((t for t in tabs
                           if t.get("type") == "page"
                           and "music.apple.com" in t.get("url", "")), None)
            return target.get("url") if target else None
        except Exception:
            return None

    def _raw_call(self, method, deadline_s=60, **params):
        """One CDP command on the existing socket. No reconnect, no retry —
        callers decide. The recv loop is hard-bounded so a zombie renderer
        can never pin a worker thread."""
        t0 = time.time()
        try:
            result = self._raw_call_inner(method, deadline_s=deadline_s, **params)
            self._record_call(method, params, time.time() - t0, ok=True)
            return result
        except Exception as e:
            self._record_call(method, params, time.time() - t0, ok=False,
                              error=str(e)[:160])
            raise

    def _record_call(self, method, params, dt, ok, error=None):
        try:
            what = str(params.get("expression") or method)[:120]
            with self._recent_lock:
                self._recent.append({
                    "ts": round(time.time(), 3), "call": method,
                    "what": what, "ms": round(dt * 1000), "ok": ok,
                    **({"error": error} if error else {})})
        except Exception:
            pass                     # diagnostics must never break the call

    def _raw_call_inner(self, method, deadline_s=60, **params):
        if self._ws is None:
            raise BrowserError(f"{method}: no websocket")
        self._n += 1
        msg_id = self._n
        deadline = time.time() + deadline_s
        try:
            self._ws.send(json.dumps({"id": msg_id, "method": method, "params": params}))
        except (websocket.WebSocketException, OSError) as e:
            raise BrowserError(f"{method}: send failed: {e}")
        while time.time() < deadline:
            try:
                msg = json.loads(self._ws.recv())
            except websocket.WebSocketTimeoutException:
                continue                        # recv slice expired — check deadline
            if msg.get("id") == msg_id:
                if "error" in msg:
                    raise BrowserError(f"{method}: {msg['error']}")
                return msg.get("result", {})
        what = params.get("expression") or params
        raise BrowserError(f"{method} timed out after {deadline_s}s: {str(what)[:120]}")

    def call(self, method, deadline_s=60, **params):
        """Raw CDP command with ONE reconnect attempt — flat, never recursive.
        The lock wait is bounded: when Chrome stalls, waiters get a fast 502
        instead of piling up behind a 60s+ zombie eval."""
        last = None
        for attempt in (1, 2):
            try:
                if not self._lock.acquire(timeout=15):
                    raise BrowserError("CDP busy — another call is in flight")
                try:
                    if self._ws is None:
                        self._connect()
                    return self._raw_call(method, deadline_s=deadline_s, **params)
                finally:
                    self._lock.release()
            except (websocket.WebSocketException, OSError, json.JSONDecodeError,
                    AttributeError, BrowserError) as e:
                last = e
                log.warning("cdp %s failed (%s), reconnecting", method, e)
                with self._lock:               # discard the poisoned socket
                    self._close_ws()
                if attempt == 2:
                    raise BrowserError(f"CDP call failed after reconnect: {e}")
                time.sleep(1)
        raise BrowserError(f"CDP call failed: {last}")

    def eval(self, js, timeout=60):
        """Evaluate JS (must be IIFE-wrapped or async IIFE), return the value.
        `timeout` is enforced CLIENT-side: Runtime.evaluate has no timeout
        parameter (passing one is silently ignored by CDP), and an
        awaitPromise eval on a promise that never resolves would otherwise
        hang the full call deadline."""
        t0 = time.time()
        res = self.call("Runtime.evaluate", expression=js, awaitPromise=True,
                        returnByValue=True, deadline_s=max(timeout, 5))
        dt = time.time() - t0
        METRICS.observe("tonearm_cdp_eval_duration_seconds", dt,
                        help_text="CDP Runtime.evaluate latency (all evals, "
                                  "including watchdog pings and stream drains)")
        if dt > 5:
            log.warning("slow eval (%.1fs): %s…", dt, js.strip()[:100])
        r = res.get("result", {})
        if r.get("subtype") == "error" or "exceptionDetails" in res:
            detail = res.get("exceptionDetails", r)
            raise BrowserError(json.dumps(detail)[:500])
        return r.get("value")

    # ------------------------------------------------------------- high level

    def wait_ready(self, timeout=30):
        """Block until window.MusicKit exists and holds a user token."""
        js = """(() => {
          try {
            const inst = window.MusicKit && MusicKit.getInstance();
            if (!inst) return {ready: false};
            return {ready: !!inst.musicUserToken, authorized: !!inst.musicUserToken};
          } catch (e) { return {ready: false}; }
        })()"""
        t0 = time.time()
        while time.time() - t0 < timeout:
            try:
                st = self.eval(js, timeout=10)
                if st and st.get("ready"):
                    return
            except Exception:
                pass
            time.sleep(1)
        raise BrowserError(
            "MusicKit is not authorized — the Chrome profile needs a one-time "
            "sign-in: run `python -m tonearm login`")

    def check(self):
        """Health probe: raises if the tab is not usable."""
        self.eval("(() => 1 + 1)()", timeout=10)
        self.wait_ready(timeout=10)

    # ------------------------------------------------------------- watchdog
    # Proactive liveness so the FIRST call after a zombie event succeeds
    # instead of eating the failure. Stall-vs-dead heuristic (the hard-won
    # part): under concurrent eval load Apple's page can stop answering for
    # ~60s AND RECOVER — so only N consecutive failed pings (default 3,
    # ~60s) count as death. A tick that can't take the lock is load, not a
    # zombie — skipped, never counted.
    # The CDP layer stays flat: the watchdog pings through _raw_call under
    # the same lock as every request, recycles via _connect (bounded, no
    # nested reconnects). Never make this recursive.

    def _watchdog_loop(self):
        log.info("renderer watchdog armed: ping every %ds, recycle after %d "
                 "consecutive failures", config.watchdog_interval,
                 config.watchdog_tries)
        while True:
            self._watchdog_armed.wait()          # sleeps until first connect
            time.sleep(config.watchdog_interval)
            if not self._watchdog_armed.is_set():
                continue
            try:
                self._watchdog_tick()
            except Exception as e:               # the watchdog must never die
                log.error("watchdog tick crashed (kept alive): %s", e)

    def _watchdog_tick(self):
        if not self._lock.acquire(timeout=0.5):
            self._wd_set(ok="skipped: request in flight")   # load, not death
            return
        try:
            if self._ws is None:
                # socket already discarded (post-failure or idle drop):
                # hot-recover now so the next call doesn't cold-start it
                try:
                    self._connect()
                except Exception as e:
                    log.warning("watchdog: reconnect attempt failed (%s)", e)
                    self._wd_set(fail=f"reconnect failed: {e}")
                    return
                self._wd_set(ok="reconnected: socket was down")
                log.info("watchdog: reconnected (socket was down)")
                return
            try:
                self._raw_call("Runtime.evaluate", expression=PING_JS,
                               returnByValue=True, deadline_s=10)
            except Exception as e:
                fails = self._wd["consecutive_failures"] + 1
                log.warning("watchdog: ping %d/%d failed (%s)", fails,
                            config.watchdog_tries, e)
                self._wd_set(fail=f"ping failed: {e}")
                if fails >= config.watchdog_tries:
                    log.warning("watchdog: tab dead after %d failed pings — "
                                "recycling", fails)
                    self._emit_webhook("renderer.stalled",
                                       {"consecutive_failures": fails,
                                        "error": str(e)[:200]})
                    self._close_ws()
                    self._connect()
                    self._wd_set(recycle=True,
                                 action="recycled: tab was dead")
                    log.info("watchdog: recycled tab, renderer healthy again")
                    self._emit_webhook("renderer.recovered",
                                       {"recycles": self._wd["recycles"]})
            else:
                self._wd_set(ok="ping ok")
        finally:
            self._lock.release()

    @staticmethod
    def _emit_webhook(event_type, data):
        """Best-effort automation event. The watchdog must never fail because
        a webhook receiver is down — emit() is already a no-op when off, and
        this swallow keeps even an import error harmless."""
        try:
            from . import webhooks
            webhooks.emit(event_type, data)
        except Exception:
            pass


# module-level singleton
browser = Browser()
