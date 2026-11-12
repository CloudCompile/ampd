"""Scheduled library exports — the cron inside the container (v0.3 #28).

/api/library/export is a complete restore reference but it's manual. This
module schedules it: one flat thread, single-flight, stall-gated (a full
export walk is ~100 s per 9k songs + every playlist's tracks — it must
never fight a limping renderer), atomic writes (tmp+rename so a killed run
can never leave a truncated "latest"), and keep-N retention (#66).

OFF by default: TONEARM_EXPORT_INTERVAL=0. When on, exports land in
TONEARM_EXPORT_DIR (default /data/exports in docker, ~/.local/share/tonearm/
exports otherwise).
"""
import json
import logging
import os
import threading
import time

from .config import config

log = logging.getLogger("tonearm.exporter")


def export_dir():
    env = os.environ.get("TONEARM_EXPORT_DIR", "")
    if env:
        return env
    if os.path.isdir("/data"):
        return "/data/exports"
    return os.path.join(os.path.expanduser("~"), ".local", "share", "tonearm",
                        "exports")


def build_export(mk_mod, songs_limit=100000):
    """The full library dump — same shape as GET /api/library/export.
    Heavy by design: walks every song and every playlist's tracks."""
    songs = mk_mod.paginated("/v1/me/library/songs?limit=100",
                             lambda d: d.get("data", []))[:songs_limit]
    playlists = mk_mod.paginated("/v1/me/library/playlists?limit=100",
                                 lambda d: d.get("data", []))
    return {
        "exported_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "song_count": len(songs),
        "songs": [mk_mod.song_row(s) for s in songs],
        "playlist_count": len(playlists),
        "playlists": [{"id": p["id"],
                       "name": p.get("attributes", {}).get("name"),
                       "tracks": [mk_mod.song_row(t) for t in
                                  mk_mod.playlist_tracks(p["id"])]}
                      for p in playlists],
    }


def write_atomic(path, payload):
    """tmp + rename — a killed run never leaves a truncated file that looks
    like a valid 'latest' export."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = f"{path}.tmp-{os.getpid()}"
    with open(tmp, "w") as f:
        json.dump(payload, f, separators=(",", ":"))
    os.replace(tmp, path)


def prune(directory, keep):
    """Delete the oldest exports past keep. Returns removed names."""
    if keep <= 0:
        return []
    files = sorted(f for f in os.listdir(directory)
                   if f.startswith("export-") and f.endswith(".json"))
    doomed = files[:-keep] if len(files) > keep else []
    for f in doomed:
        try:
            os.unlink(os.path.join(directory, f))
        except OSError as e:
            log.warning("export prune failed for %s: %s", f, e)
    return doomed


class ExportScheduler(threading.Thread):
    """TONEARM_EXPORT_INTERVAL seconds between full exports. Single-flight,
    stall-gated. `build_fn` is injected so tests run without a renderer."""

    def __init__(self, browser_instance, mk_mod, interval=None, keep=None,
                 build_fn=None, directory=None, store=None):
        super().__init__(daemon=True, name="tonearm-export-scheduler")
        self._browser = browser_instance
        self._mk = mk_mod
        self.interval = interval or config.export_interval
        self.keep = keep if keep is not None else config.export_keep
        self._build_fn = build_fn or build_export
        self.dir = directory or export_dir()
        self.store = store            # optional — cursors when the store is on
        self._busy = threading.Lock()
        self._stop = threading.Event()

    def stop(self):
        self._stop.set()

    def _stalled(self):
        try:
            wd = self._browser.health()
        except Exception:
            return True
        if wd.get("last_ok") is False or \
                (wd.get("consecutive_failures") or 0) > 0:
            return True
        return False

    def run_export(self):
        """One export. Returns the summary; safe to call directly."""
        if not self._busy.acquire(timeout=0.1):
            return {"ran": False, "reason": "previous export still running"}
        try:
            t0 = time.time()
            payload = self._build_fn(self._mk)
            name = time.strftime("export-%Y%m%d-%H%M%S.json")
            path = os.path.join(self.dir, name)
            write_atomic(path, payload)
            removed = prune(self.dir, self.keep)
            summary = {"ran": True, "file": name,
                       "songs": payload["song_count"],
                       "playlists": payload["playlist_count"],
                       "pruned": len(removed),
                       "seconds": round(time.time() - t0, 1)}
            if self.store and self.store.enabled:
                try:
                    self.store.set_cursor("export.last_run", summary)
                except Exception:
                    pass
            log.info("export written: %s (%d songs, %d playlists, %.0fs)",
                     name, payload["song_count"], payload["playlist_count"],
                     summary["seconds"])
            return summary
        except Exception as e:
            log.error("export failed (kept alive): %s", e)
            return {"ran": False, "reason": str(e)[:200]}
        finally:
            self._busy.release()

    def run(self):
        log.info("export scheduler armed: every %ds, keep %d, dir %s",
                 self.interval, self.keep, self.dir)
        while not self._stop.wait(self.interval):
            if self._stalled():
                continue
            self.run_export()
