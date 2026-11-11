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

import websocket

from .config import config

log = logging.getLogger("ampd.browser")

MUSIC_URL = "https://music.apple.com/"


class BrowserError(RuntimeError):
    pass


class Browser:
    """Owns the single Music tab. All methods are thread-safe."""

    def __init__(self):
        self._lock = threading.RLock()
        self._ws = None
        self._target_id = None
        self._n = 0

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
                "Start one or set AMPD_AUTO_CHROME=1.")
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

    def _connect(self):
        """Attach to (creating if needed) the persistent music tab."""
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
        self._ws = websocket.create_connection(
            target["webSocketDebuggerUrl"], timeout=60, max_size=100 * 1024 * 1024)
        self._n = 0
        self.call("Page.enable")
        self.call("Runtime.enable")
        # park the tab on Apple Music and wait for MusicKit to be ready
        if "music.apple.com" not in target.get("url", ""):
            self.call("Page.navigate", url=MUSIC_URL)
            time.sleep(4)
        self.wait_ready(timeout=30)

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

    def call(self, method, **params):
        """Raw CDP command with auto-reconnect."""
        for attempt in (1, 2):
            try:
                if self._ws is None:
                    self._connect()
                self._n += 1
                msg_id = self._n
                self._ws.send(json.dumps({"id": msg_id, "method": method, "params": params}))
                deadline = time.time() + 120
                while time.time() < deadline:
                    msg = json.loads(self._ws.recv())
                    if msg.get("id") == msg_id:
                        if "error" in msg:
                            raise BrowserError(f"{method}: {msg['error']}")
                        return msg.get("result", {})
                raise BrowserError(f"{method}: timed out")
            except (websocket.WebSocketException, OSError, json.JSONDecodeError,
                    AttributeError) as e:
                log.warning("cdp %s failed (%s), reconnecting", method, e)
                self._close_ws()
                if attempt == 2:
                    raise BrowserError(f"CDP call failed after reconnect: {e}")
                time.sleep(1)
                self._connect()

    def eval(self, js, timeout=60):
        """Evaluate JS (must be IIFE-wrapped or async IIFE), return the value."""
        res = self.call("Runtime.evaluate", expression=js, awaitPromise=True,
                        returnByValue=True, timeout=timeout * 1000)
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
            "sign-in: run `python -m ampd login`")

    def check(self):
        """Health probe: raises if the tab is not usable."""
        self.eval("(() => 1 + 1)()", timeout=10)
        self.wait_ready(timeout=10)


# module-level singleton
browser = Browser()
