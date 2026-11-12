"""Listening history — the local archive (v0.3 Memory).

Apple's recently-played endpoint caps at ~20 items and erodes forever.
The local store (ampd/store.py) persists every track start as it happens,
riding the stream-hook buffer — zero new eval kinds. This router serves the
REAL archive, and answers 501 when the store is off (honest opt-in).
"""
from fastapi import APIRouter, HTTPException

from .. import musickit as mk  # noqa: F401  (pattern parity with sibling routers)
from ..store import StoreDisabled, store

router = APIRouter(prefix="/history", tags=["history (local store)"])


@router.get("/recently-played")
def recently_played(limit: int = 50, offset: int = 0):
    """Everything you've played since AMPD_STORE=1 was first enabled,
    newest first. No backfill: Apple only ever exposed ~20 recent items,
    so coverage starts when the store turns on."""
    try:
        return store.recently_played(limit=limit, offset=offset)
    except StoreDisabled as e:
        raise HTTPException(501, str(e))
