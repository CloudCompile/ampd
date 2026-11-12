"""New-release watcher surface (v0.6 #42).

The loop lives in `tonearm/watcher.py`; this router is the operator's
window: state read from the store, plus a synchronous single pass for the
verify-live work the feature is gated on. Reads are eval-free (store +
memory only — the /api/debug discipline); the refresh route does real
Apple work, so it is gated like everything that talks to Apple.

Routes:
  GET  /api/watcher           state: watched artists, mapping coverage,
                              last pass summary
  POST /api/watcher/refresh   one bounded pass, synchronously (same as the
                              scheduler's tick)
"""
from fastapi import APIRouter

from .. import watcher as watcher_mod
from ..config import config
from ..errors import ApiError
from ..models import Ok, WatcherInfo, WatcherPass
from ..store import StoreDisabled, store

router = APIRouter(prefix="/watcher", tags=["watcher (automation)"])


def _disabled(e):
    return ApiError(501, "store_disabled", str(e))


def _off():
    return ApiError(501, "watcher_disabled",
                    "the release watcher is off — set TONEARM_WATCHER=1 "
                    "(and see the verify-live note in the README: the "
                    "artist->catalog mapping strategy is unverified "
                    "against a real Apple account)")


@router.get("", response_model=WatcherInfo)
def info():
    """Watcher state. Artists that have never resolved to a catalog id are
    reported honestly (`mapped` vs `watched`) — a bad mapping is data, not
    a silent zero."""
    try:
        artists = store.watcher_artists()
        last = store.get_cursor("watcher.pass") or {}
    except StoreDisabled as e:
        raise _disabled(e)
    mapped = [a for a in artists if a.get("catalog_artist_id")]
    return {"enabled": config.watcher_enabled,
            "interval": config.watcher_interval,
            "max_artists_per_pass": config.watcher_max_artists,
            "auto_playlist": config.watcher_auto_playlist or None,
            "auto_add_active": bool(config.watcher_auto_playlist
                                    and config.enable_writes),
            "watched": len(artists),
            "mapped": len(mapped),
            "unmapped": len(artists) - len(mapped),
            "artists": artists,
            "last_pass": last or None}


@router.post("/refresh", response_model=WatcherPass)
def refresh():
    """One bounded pass, synchronously. Same code the scheduler runs —
    useful for the live verification (and for cron'ing it yourself)."""
    if not config.watcher_enabled:
        raise _off()
    w = watcher_mod.watcher
    if w is None:
        # armed-but-not-started (e.g. webhooks off with no auto-add target)
        raise ApiError(501, "watcher_not_running",
                       "watcher is enabled but not running — check the "
                       "startup log (it refuses to start with nothing to "
                       "notify and nowhere to add)")
    summary = w.run_pass()
    if not summary.get("ran"):
        raise ApiError(409, "busy", summary.get("reason", "try again"))
    return summary
