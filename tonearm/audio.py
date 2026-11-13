"""Audio streaming — make the music HEARABLE off-box.

The problem: on a VPS, chrome plays into the void. A custom UI at home gets
metadata from /api/stream but silence. This module closes the loop:

    chrome ──PULSE_SINK──> null sink "tonearm_audio" ──monitor──> parec
        └─> ffmpeg ──> per-format broadcaster ──> GET /api/audio/stream.{ext}

The sink is private (the desktop's own audio never touches it) and the
stream is the audio your already-authenticated session is playing — for
one listener, that's your own music with extra steps.

Formats (v0.5 #92): mp3 (default, back-compat URL), ogg (vorbis), opus.
Each ACTIVE format gets its own encoder reading the same monitor — the
capture stays the one source; encoders are per-format (started on first
listener of that format, stopped when its last listener leaves — never per
listener). Loudness normalization (#93) is an ffmpeg filter in the same
pipeline process — still one subprocess per (format, bitrate, loudnorm)
combination, fanned out post-encode.

Join alignment (#95): the capture is a LIVE PIPE, never a seekable buffer —
a mid-song listener cannot seek. On subscribe the feed is padded with
pre-encoded silence so clients have a deterministic alignment point, and
the response carries X-Tonearm-Join-* headers describing where the playhead
was at join. Best-effort by design: when the playhead state is stale, the
headers say so loudly instead of pretending.

Everything is best-effort on setup: if pulse/ffmpeg are missing, the
pipeline reports it in /api/audio/status instead of crashing the server.
"""
import logging
import os
import re
import queue
import shutil
import subprocess
import threading

from .config import config

log = logging.getLogger("tonearm.audio")

# encoder recipes — same capture, different tails. opus runs 48 kHz (the
# codec rejects 44.1); ogg/opus both ride the ogg muxer for browser compat.
FORMATS = {
    "mp3":  {"codec": "libmp3lame", "muxer": "mp3", "type": "audio/mpeg",
             "rate": 44100},
    "ogg":  {"codec": "libvorbis",  "muxer": "ogg", "type": "audio/ogg",
             "rate": 44100},
    "opus": {"codec": "libopus",    "muxer": "ogg", "type": "audio/ogg",
             "rate": 48000},
}

BITRATE_RE = re.compile(r"^\d{2,3}k?$")
LOUDNORM = "loudnorm=I=-16:TP=-1.5:LRA=11"   # streaming target: -16 LUFS
SILENCE_SECS = 2                              # pre-encoded join pad length


class AudioError(RuntimeError):
    pass


# playhead state, fed by the SSE stream (routes/stream.py) on every event —
# the join alignment reads THIS, never Chrome, never a seekable buffer
_playhead = {"elapsed_ms": None, "playing": False, "ts": 0}
_playhead_lock = threading.Lock()


def note_playhead(elapsed_ms, playing):
    """Called by the SSE stream on every snapshot/update. Stale-tolerant:
    the join code decides staleness by its own clock."""
    import time
    with _playhead_lock:
        _playhead.update(elapsed_ms=elapsed_ms, playing=bool(playing),
                         ts=time.time())


def join_playhead(max_age=10.0):
    """(playhead_ms, is_stale) at subscribe time. Stale = say so loudly,
    never guess (the pipe is live; a wrong alignment claim is a lie)."""
    import time
    with _playhead_lock:
        age = time.time() - _playhead["ts"]
        return _playhead["elapsed_ms"], age > max_age


class Pipeline:
    """One parec|ffmpeg encoder for one (format, bitrate, loudnorm) key."""

    def __init__(self, fmt, bitrate, loudnorm):
        self.key = (fmt, bitrate, loudnorm)
        self.fmt = fmt
        self.spec = FORMATS[fmt]
        self.bitrate = bitrate
        self.loudnorm = loudnorm
        self._lock = threading.Lock()
        self._subs: set[queue.Queue] = set()
        self._proc = None
        self._error = None
        self._started = False
        self._silence = b""        # pre-encoded join pad (SILENCE_SECS long)

    def _filter_args(self):
        return ["-af", LOUDNORM] if self.loudnorm else []

    def _ffmpeg_tail(self):
        s = self.spec
        return (f"-c:a {s['codec']} -b:a {self.bitrate} "
                f"-ar {s['rate']} -ac 2 -f {s['muxer']} pipe:1")

    def start(self):
        with self._lock:
            if self._started:
                return
            if not shutil.which("parecord") or not shutil.which("ffmpeg"):
                raise AudioError("audio streaming needs pulseaudio-utils "
                                 "(parecord) and ffmpeg on PATH")
            b = Broadcaster()
            b.ensure_pulse()
            b.ensure_sink(config.audio_sink)
            cmd = (
                "parecord --device={sink}.monitor --format=s16le --rate=44100 "
                "--channels=2 --raw | ffmpeg -loglevel error -f s16le "
                "-ar 44100 -ac 2 -i - {filter} {tail}"
            ).format(sink=config.audio_sink,
                     filter=" ".join(self._filter_args()),
                     tail=self._ffmpeg_tail())
            log.info("audio pipeline %s: %s", self.key, cmd)
            self._proc = subprocess.Popen(
                ["sh", "-c", cmd], stdout=subprocess.PIPE,
                stderr=open("/tmp/tonearm-audio-pipeline.log", "ab"),
                env=b._env(), start_new_session=True)
            self._started = True
            self._silence = self._encode_silence()
            threading.Thread(target=self._read, daemon=True,
                             name="tonearm-audio-%s" % (self.key,)).start()

    def stop(self):
        """Kill the capture subprocesses. They run in their OWN session
        (start_new_session) — a graceful server exit does NOT deliver
        signals to them (#177, found live: a 'stopped' server left
        parecord running for minutes, recording silence from a dead
        sink)."""
        with self._lock:
            proc, self._proc, self._started = self._proc, None, False
        if proc and proc.poll() is None:
            import signal
            import os as _os
            try:                       # the whole sh -c group: parecord+ffmpeg
                _os.killpg(_os.getpgid(proc.pid), signal.SIGTERM)
            except (ProcessLookupError, PermissionError):
                try:
                    proc.terminate()
                except Exception:
                    pass

    def _encode_silence(self):
        """Pre-encode SILENCE_SECS of true silence with the SAME codec args —
        the join pad has exactly the stream's format. One cheap one-shot at
        pipeline boot; failure is non-fatal (pad becomes b"")."""
        cmd = ("ffmpeg -loglevel error -f lavfi "
               f"-i anullsrc=r={self.spec['rate']}:cl=stereo -t {SILENCE_SECS} "
               f"{self._ffmpeg_tail()}")
        try:
            r = subprocess.run(["sh", "-c", cmd], capture_output=True,
                               timeout=30, env=Broadcaster()._env())
            if r.returncode == 0 and r.stdout:
                return r.stdout
        except Exception as e:
            log.warning("silence pad encode failed (%s): %s", self.key, e)
        return b""

    def _read(self):
        assert self._proc and self._proc.stdout
        while True:
            chunk = self._proc.stdout.read(4096)
            if not chunk:
                err = self._proc.stderr.read(512) if self._proc.stderr else b""
                self._error = (err or b"capture pipeline ended").decode(
                    errors="replace")
                self._started = False
                return
            for q in list(self._subs):
                try:
                    q.put_nowait(chunk)            # live stream: drop if slow
                except Exception:
                    pass                           # queue full — client lagged


class Broadcaster:
    """The capture source fans out to per-format encoders; each encoder
    fans out to its listeners. Lazily started per (format, bitrate,
    loudnorm) on first listener, stopped when the last one leaves."""

    def __init__(self):
        self._lock = threading.Lock()
        self._pipelines: dict[tuple, Pipeline] = {}

    # ---------------------------------------------------------------- setup
    # (kept on Broadcaster for back-compat — Pipeline reuses them)

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

    # ------------------------------------------------------------ subscribe

    def subscribe(self, fmt="mp3", bitrate=None, loudnorm=None):
        """(queue, join_meta) for one listener of one format.

        join_meta: {pad_ms, playhead_ms, stale} — the response headers are
        built from this (#95). Stale playhead => pad still applies (it is
        just an alignment point) but the header says the playhead claim is
        unreliable. Degrade loudly, never silently pretend.
        """
        bitrate = bitrate or config.audio_bitrate
        if not BITRATE_RE.match(bitrate or ""):
            raise AudioError(f"bad bitrate {bitrate!r} — use e.g. 96k, 160k, 320k")
        loudnorm = config.audio_loudnorm if loudnorm is None else loudnorm
        key = (fmt, bitrate, bool(loudnorm))
        with self._lock:
            pipe = self._pipelines.get(key)
            if pipe is None:
                pipe = Pipeline(*key)
                self._pipelines[key] = pipe
            pipe.start()                             # no-op when running
            q = queue.Queue(maxsize=512)
            q._tonearm_pipeline = pipe                  # unsubscribe routing
            pipe._subs.add(q)
        playhead_ms, stale = join_playhead()
        pad_ms = SILENCE_SECS * 1000 if config.audio_join_pad else 0
        if pad_ms and pipe._silence:
            q.put_nowait(pipe._silence)
        return q, {"pad_ms": pad_ms if pipe._silence else 0,
                   "playhead_ms": playhead_ms, "stale": stale,
                   "format": fmt, "bitrate": bitrate,
                   "loudnorm": bool(loudnorm)}

    def unsubscribe(self, q):
        pipe = getattr(q, "_tonearm_pipeline", None)
        if pipe is None:
            return
        with self._lock:
            pipe._subs.discard(q)
            if not pipe._subs and self._pipelines.get(pipe.key) is pipe:
                # last listener of this format left — stop the encoder
                del self._pipelines[pipe.key]
        pipe.stop()

    def prestart(self, fmt="mp3", bitrate=None, loudnorm=None):
        """Eager-start the default pipeline at boot — BEFORE the process is
        multithreaded: spawning subprocesses from the running event loop
        wedges the loop (fork-vs-GIL deadlock, found with py-spy the hard
        way). Extra formats still start lazily via the routes' to_thread."""
        bitrate = bitrate or config.audio_bitrate
        loudnorm = config.audio_loudnorm if loudnorm is None else loudnorm
        key = (fmt, bitrate, bool(loudnorm))
        with self._lock:
            pipe = self._pipelines.setdefault(key, Pipeline(*key))
        pipe.start()

    def stop(self):
        """Teardown (#177): kill every capture pipeline's subprocesses.
        Without this, a 'stopped' server left parecord|ffmpeg running in
        their own session — recording silence from a dead sink for
        nobody."""
        with self._lock:
            pipes = list(self._pipelines.values())
        for p in pipes:
            try:
                p.stop()
            except Exception:
                pass

    def status(self):
        with self._lock:
            pipes = list(self._pipelines.values())
        return {"running": bool(pipes),
                "listeners": sum(len(p._subs) for p in pipes),
                "sink": config.audio_sink,
                "bitrate": config.audio_bitrate,
                "error": next((p._error for p in pipes if p._error), None),
                "pipelines": [{"format": p.fmt, "bitrate": p.bitrate,
                               "loudnorm": p.loudnorm,
                               "listeners": len(p._subs),
                               "running": p._started} for p in pipes]}


broadcaster = Broadcaster()
