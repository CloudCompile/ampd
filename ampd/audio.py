"""Audio streaming — make the music HEARABLE off-box.

The problem: on a VPS, chrome plays into the void. A custom UI at home gets
metadata from /api/stream but silence. This module closes the loop:

    chrome ──PULSE_SINK──> null sink "ampd_audio" ──monitor──> parec
        └─> ffmpeg (mp3) ──> broadcaster ──> GET /api/audio/stream.mp3

The sink is private (the desktop's own audio never touches it) and the
stream is the audio your already-authenticated session is playing — for
one listener, that's your own music with extra steps.

Everything is best-effort on setup: if pulse/ffmpeg are missing, the
pipeline reports it in /api/audio/status instead of crashing the server.
"""
import logging
import os
import queue
import shutil
import subprocess
import threading

from .config import config

log = logging.getLogger("ampd.audio")


class AudioError(RuntimeError):
    pass


class Broadcaster:
    """One capture pipeline, fanned out to any number of listeners."""

    def __init__(self):
        self._lock = threading.Lock()
        self._subs: set[object] = set()   # of queue.Queue
        self._proc: subprocess.Popen | None = None
        self._thread: threading.Thread | None = None
        self._error: str | None = None
        self._started = False

    # ---------------------------------------------------------------- setup

    def _env(self):
        env = dict(os.environ)
        if "XDG_RUNTIME_DIR" not in env:            # headless shells / containers
            env["XDG_RUNTIME_DIR"] = f"/run/user/{os.getuid()}"
        return env

    def ensure_pulse(self):
        """Have a reachable pulse daemon (starts one for containers/VPS)."""
        env = self._env()
        r = subprocess.run(["pactl", "info"], capture_output=True, timeout=15, env=env)
        if r.returncode == 0:
            return True
        os.makedirs(env["XDG_RUNTIME_DIR"], exist_ok=True)
        subprocess.run(["pulseaudio", "--start", "--exit-idle-time=-1",
                        "--disable-shm"], capture_output=True, timeout=30, env=env)
        r = subprocess.run(["pactl", "info"], capture_output=True, timeout=15, env=env)
        if r.returncode != 0:
            raise AudioError("pulseaudio is not reachable (pactl info failed)")
        return True

    def ensure_sink(self, name):
        """Create the private null sink (no-op if it exists)."""
        env = self._env()
        r = subprocess.run(["pactl", "list", "short", "sinks"],
                           capture_output=True, text=True, timeout=15, env=env)
        if any(line.split()[1] == name
               for line in r.stdout.splitlines() if line.strip()):
            return True                              # already there — do NOT
        r = subprocess.run(                          # load a duplicate
            ["pactl", "load-module", "module-null-sink", f"sink_name={name}",
             f'sink_properties=device.description="{name}"'],
            capture_output=True, text=True, timeout=15, env=env)
        return r.returncode == 0

    def ensure_display(self, display):
        """Make sure the virtual X display exists (spawn Xvfb if not)."""
        num = display.lstrip(":").split(".")[0]
        if os.path.exists(f"/tmp/.X11-unix/X{num}"):
            return True
        subprocess.Popen(["Xvfb", display, "-screen", "0", "1400x900x24"],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         start_new_session=True)
        import time
        for _ in range(20):
            time.sleep(0.5)
            if os.path.exists(f"/tmp/.X11-unix/X{num}"):
                return True
        raise AudioError(f"Xvfb {display} did not come up")

    # ------------------------------------------------------------ pipeline

    def start(self):
        with self._lock:
            if self._started:
                return
            if not shutil.which("parecord") or not shutil.which("ffmpeg"):
                raise AudioError("audio streaming needs pulseaudio-utils "
                                 "(parecord) and ffmpeg on PATH")
            self.ensure_pulse()
            self.ensure_sink(config.audio_sink)
            cmd = (
                "parecord --device={sink}.monitor --format=s16le --rate=44100 "
                "--channels=2 --raw | ffmpeg -loglevel error -f s16le "
                "-ar 44100 -ac 2 -i - -c:a libmp3lame -b:a {br} -f mp3 pipe:1"
            ).format(sink=config.audio_sink, br=config.audio_bitrate)
            log.info("audio pipeline: %s", cmd)
            self._proc = subprocess.Popen(
                ["sh", "-c", cmd], stdout=subprocess.PIPE,
                stderr=open("/tmp/ampd-audio-pipeline.log", "ab"),
                env=self._env(), start_new_session=True)
            self._started = True
            self._thread = threading.Thread(target=self._read, daemon=True)
            self._thread.start()

    def _read(self):
        assert self._proc and self._proc.stdout
        while True:
            chunk = self._proc.stdout.read(4096)
            if not chunk:
                err = self._proc.stderr.read(512) if self._proc.stderr else b""
                self._error = (err or b"capture pipeline ended").decode(errors="replace")
                self._started = False
                return
            for q in list(self._subs):
                try:
                    q.put_nowait(chunk)            # live stream: drop if slow
                except Exception:
                    pass                           # queue full — client lagged

    # ----------------------------------------------------------- subscribe

    def subscribe(self):
        q = queue.Queue(maxsize=512)
        with self._lock:
            if not self._started:
                self.start()                       # lazy start on first listener
            self._subs.add(q)
        return q

    def unsubscribe(self, q):
        with self._lock:
            self._subs.discard(q)

    def status(self):
        return {"running": self._started, "listeners": len(self._subs),
                "sink": config.audio_sink, "bitrate": config.audio_bitrate,
                "error": self._error}


broadcaster = Broadcaster()
