"""Listening history — the local archive (v0.3 Memory).

Apple's recently-played endpoint caps at ~20 items and erodes forever.
The local store (ampd/store.py) persists every track start as it happens,
riding the stream-hook buffer — zero new eval kinds. This router serves the
REAL archive, and answers 501/store_disabled when the store is off (honest
opt-in).

Stats are pure local computation — no Apple calls, aggregation in SQL.
"""
import time

from fastapi import APIRouter, HTTPException

from ..errors import ApiError
from ..store import StoreDisabled, store

router = APIRouter(prefix="/history", tags=["history (local store)"])

_WINDOWS = {"day": 86400.0, "week": 604800.0, "month": 2592000.0}


@router.get("/recently-played")
def recently_played(limit: int = 50, offset: int = 0):
    """Everything you've played since AMPD_STORE=1 was first enabled,
    newest first. No backfill: Apple only ever exposed ~20 recent items,
    so coverage starts when the store turns on."""
    try:
        return store.recently_played(limit=limit, offset=offset)
    except StoreDisabled as e:
        raise ApiError(501, "store_disabled", str(e))


@router.get("/stats")
def stats(window: str = "all", limit: int = 25):
    """Top artists / tracks from the LOCAL play archive (not Apple's).
    window: day | week | month | all. Plays dedupe on (track_id, started_at)
    is the writer's guarantee, so counts are play-starts."""
    if window not in _WINDOWS and window != "all":
        raise HTTPException(400, "window is day | week | month | all")
    since = time.time() - _WINDOWS[window] if window in _WINDOWS else 0
    try:
        return store.stats(since=since, limit=min(limit, 100))
    except StoreDisabled as e:
        raise ApiError(501, "store_disabled", str(e))


@router.get("/stats/series")
def stats_series(days: int = 30):
    """Plays per day, last N days — bucketed in SQL, ready for a chart."""
    since = time.time() - min(days, 3650) * 86400.0
    try:
        return {"days": days,
                "series": store.plays_series(since=since)}
    except StoreDisabled as e:
        raise ApiError(501, "store_disabled", str(e))
