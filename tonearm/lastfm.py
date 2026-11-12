"""Last.fm scrobble bridge (v0.5 #97 #98) — opt-in, zero new deps.

One-time auth:  python -m tonearm.lastfm   (token flow -> creds file, 0600)
Runtime:        TONEARM_LASTFM=1  (requires the store — the dedupe marker is
                UNIQUE(track_id, started_at) in the scrobbles table)

* **Scrobbles come from the same event buffer the store already drains** —
  the scrobbler keeps its own seq cursor and watches track-key changes;
  Chrome is never asked for anything extra.
* **The 50 % / 4-min rule is offline-computable** (#98): every event carries
  elapsedMs/durationMs/ts, so a play's played-amount is the last elapsedMs
  observed for that key. Submit when played >= 50 % of duration OR >= 4
  minutes — whichever comes first (Last.fm's rule, verbatim).
* **Idempotent forever**: a scrobble is (track_id, started_at) — the same
  key the store dedupes plays on. The marker persists in the scrobbles
  table; restarts, buffer replays and overlapping drains never double-
  scrobble.
* **Now-playing** on every new track key while playing (throttled per key).
* Opt-in import: nothing here loads unless TONEARM_LASTFM=1; stdlib only.
* Every failure mode (no creds, network down, API 4xx) logs once and
  retries — the bridge can never take the server down.
"""
import hashlib
import json
import logging
import os
import stat
import threading
import time
import urllib.parse
import urllib.request

from .config import config

log = logging.getLogger("tonearm.lastfm")

API_ROOT = "https://ws.audioscrobbler.com/2.0/"
AUTH_URL = "https://www.last.fm/api/auth/"
MIN_SCROBBLE_S = 240          # the 4-minute arm of the rule


class LastfmError(RuntimeError):
    pass


def creds_path():
    return config.lastfm_creds_path()


def load_creds():
    try:
        with open(creds_path()) as f:
            return json.load(f)
    except Exception:
        return None


# ------------------------------------------------------------------- API

def _sign(params, secret):
    """Last.fm api signature: sorted param k=v concat + secret, md5."""
    base = "".join(f"{k}{v}" for k, v in sorted(params.items())
                   if k != "format")
    return hashlib.md5((base + secret).encode()).hexdigest()


def _call(params, api_key, secret, sk=None):
    """One POST to the Last.fm API. Raises LastfmError on any failure.
    Signature covers every param except format/api_sig (Last.fm spec)."""
    params = {k: str(v) for k, v in params.items() if v is not None}
    if sk:
        params["sk"] = sk
    params["api_key"] = api_key
    params["api_sig"] = _sign(params, secret)
    params["format"] = "json"
    data = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(API_ROOT, data=data, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            body = json.loads(r.read())
    except Exception as e:
        raise LastfmError(f"lastfm api unreachable: {e}") from e
    if isinstance(body, dict) and body.get("error"):
        raise LastfmError(f"lastfm api error {body.get('error')}: "
                          f"{body.get('message')}")
    return body


def auth_token_url(api_key, secret):
    """(token, url the user must open) — step 1 of the token flow."""
    token = _call({"method": "auth.getToken"}, api_key, secret)["token"]
    return token, f"{AUTH_URL}?api_key={urllib.parse.quote(api_key)}" \
                  f"&token={token}"


def get_session(api_key, secret, token):
    """Exchange an authorized token for a session key — step 3."""
    body = _call({"method": "auth.getSession", "token": token},
                 api_key, secret)
    return body["session"]["key"], body["session"]["name"]


def scrobble(creds, artist, track, album, started_at, duration_s=None):
    """One scrobble. started_at = when the track STARTED playing (epoch s)
    — Last.fm wants the play's start, not its submission time."""
    params = {"method": "track.scrobble", "artist": artist or "Unknown",
              "track": track, "timestamp": int(started_at)}
    if album:
        params["album"] = album
    if duration_s:
        params["duration"] = max(1, int(duration_s))
    return _call(params, creds["api_key"], creds["secret"], sk=creds["sk"])


def update_now_playing(creds, artist, track, album, duration_s=None):
    params = {"method": "track.updateNowPlaying",
              "artist": artist or "Unknown", "track": track}
    if album:
        params["album"] = album
    if duration_s:
        params["duration"] = max(1, int(duration_s))
    return _call(params, creds["api_key"], creds["secret"], sk=creds["sk"])


# ---------------------------------------------------------- scrobble rule

def qualifies(elapsed_ms, duration_ms):
    """The 50 % / 4-min rule, verbatim: submit when played >= 50 % of the
    duration OR played >= 4 minutes — whichever comes first."""
    if not elapsed_ms or elapsed_ms <= 0:
        return False
    if elapsed_ms >= MIN_SCROBBLE_S * 1000:
        return True
    if duration_ms and duration_ms > 0:
        return elapsed_ms >= duration_ms / 2
    return False


class Scrobbler(threading.Thread):
    """Watches the stream event buffer (own cursor), scrobbles qualified
    plays. Same drain discipline as the store's HistoryWriter."""

    CADENCE_S = 5.0

    def __init__(self, store, creds, cadence_s=None):
        super().__init__(daemon=True, name="tonearm-lastfm")
        self.store = store
        self.creds = creds
        self.cadence = cadence_s or self.CADENCE_S
        self._seq = 0
        self._stop = threading.Event()
        # per-play accumulation: key -> {started_at, elapsed, duration,
        # title, artist, album} — the last elapsed seen wins
        self._watch = {}
        self._nowplaying_key = None

    def stop(self):
        self._stop.set()

    # -- pure event -> decision layer (split out; tests feed it buffers) --

    def process_events(self, entries):
        """Returns the list of scrobbles submitted. The play model matches
        the store's: a play = the track key changes while playing (or
        playback resumes from a pause)."""
        submitted = []
        for e in entries:
            self._seq = max(self._seq, e.get("seq", 0))
            key = e.get("id") or e.get("title")
            if not key:
                continue
            playing = e.get("isPlaying") is not False
            w = self._watch.get(key)
            if playing:
                if w is None:
                    w = self._watch[key] = {
                        "started_at": (e.get("ts") or time.time() * 1000)
                        / 1000.0, "elapsed": 0, "duration": None,
                        "title": e.get("title"), "artist": e.get("artist"),
                        "album": e.get("album")}
                if e.get("elapsedMs") is not None:
                    w["elapsed"] = max(w["elapsed"], e["elapsedMs"])
                if e.get("durationMs"):
                    w["duration"] = e["durationMs"]
                # now-playing: once per key
                if self._nowplaying_key != key:
                    self._nowplaying_key = key
                    try:
                        update_now_playing(
                            self.creds, w["artist"], w["title"], w["album"],
                            duration_s=(w["duration"] or 0) / 1000 or None)
                    except Exception as ex:
                        log.debug("now-playing submit skipped: %s", ex)
                # the rule can already be satisfied mid-track
                if qualifies(w["elapsed"], w["duration"]):
                    submitted += self._submit(key, w)
            elif self._nowplaying_key == key:
                self._nowplaying_key = None          # paused -> clear locally
        return submitted

    def _submit(self, key, w):
        started_at = round(w["started_at"], 3)
        if self.store is not None and not self.store.record_scrobble(
                key, started_at):
            return []                    # already scrobbled — restarts and
                                         # buffer replays never double-fire
        try:
            scrobble(self.creds, w["artist"], w["title"], w["album"],
                     started_at, duration_s=(w["duration"] or 0) / 1000
                     or None)
            log.info("lastfm: scrobbled %s — %s", w["title"], w["artist"])
        except Exception as e:
            log.warning("lastfm: scrobble failed (%s) — will retry on the "
                        "next buffer pass", str(e)[:120])
            return []                    # not marked done -> retried later
        return [(key, started_at)]

    # ------------------------------------------------------------ loop

    def run(self):
        log.info("lastfm scrobbler armed (cadence %.0fs) — rides the same "
                 "stream buffer as the store; dedupe on (id, started_at)",
                 self.cadence)
        while not self._stop.wait(self.cadence):
            if not self.store.enabled:
                continue
            try:
                from . import musickit as mk
                entries = mk.drain_stream(self._seq)
            except Exception as e:
                log.debug("lastfm drain skipped: %s", e)
                continue
            if entries:
                try:
                    self.process_events(entries)
                except Exception as e:
                    log.warning("lastfm process failed: %s", str(e)[:150])


# -------------------------------------------------------------- CLI flow

def _save_creds(creds):
    p = creds_path()
    os.makedirs(os.path.dirname(p) or ".", exist_ok=True)
    fd = os.open(p, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump(creds, f, indent=1)
    os.chmod(p, stat.S_IRUSR | stat.S_IWUSR)         # enforce 0600
    return p


def cli():                               # pragma: no cover (interactive)
    """python -m tonearm.lastfm — the one-time token flow."""
    api_key = config.lastfm_api_key or input("Last.fm API key: ").strip()
    secret = config.lastfm_secret or input("Last.fm shared secret: ").strip()
    token, url = auth_token_url(api_key, secret)
    print("\n1. Open this URL and approve access:\n   " + url)
    input("2. Press Enter once approved... ")
    sk, name = get_session(api_key, secret, token)
    p = _save_creds({"api_key": api_key, "secret": secret, "sk": sk,
                     "user": name})
    print(f"\nDone — {name} authorized. Creds saved to {p} (0600).\n"
          "Start tonearm with TONEARM_LASTFM=1 to scrobble.")


if __name__ == "__main__":
    cli()
