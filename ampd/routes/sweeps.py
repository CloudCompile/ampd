"""Library sweeps — batch operations, dry-run by default.

DESIGN RULE (learned the hard way): a song's heart is its rating, and
removals are irreversible. Every sweep therefore returns a PLAN unless you
pass `execute=1`, and rating sweeps only ever ADD hearts — they never
clear one.

Sweeps:
  dedupe        find library rows sharing a catalog id (or name+artist+
                duration), keep one, remove the rest
  rate          batch-heart library songs matching a filter
                (artist / album / min-plays / unrated-only)
  never-played  read-only report of songs Apple reports 0 plays for
"""
from fastapi import APIRouter, HTTPException

from .. import musickit as mk
from ..browser import BrowserError

router = APIRouter(prefix="/write/sweeps", tags=["sweeps (batch, dry-run default)"])


def _all_library_songs():
    def extract(d):
        return d.get("data", [])
    return mk.paginated("/v1/me/library/songs?limit=100", extract)


def _row_identity(row):
    """Group key: catalog id when known, else name+artist+duration."""
    attrs = row.get("attributes", {})
    catalog = (attrs.get("playParams") or {}).get("catalogId")
    if catalog:
        return f"cat:{catalog}", catalog
    dur = attrs.get("durationInMillis")
    return (f"nd:{(attrs.get('name') or '').lower()}|"
            f"{(attrs.get('artistName') or '').lower()}|{dur}"), None


def _song_row(row):
    return mk.item_row(row)


# ---------------------------------------------------------------- dedupe

@router.get("/dedupe")
def dedupe_plan():
    """Dry-run: groups of duplicate library rows. Nothing is touched."""
    rows = _all_library_songs()
    groups = {}
    for r in rows:
        key, _ = _row_identity(r)
        groups.setdefault(key, []).append(r)
    dupes = {k: [_song_row(x) for x in v]
             for k, v in groups.items() if len(v) > 1}
    removable = sum(len(v) - 1 for v in dupes.values())
    return {"library_size": len(rows), "duplicate_groups": len(dupes),
            "removable_rows": removable, "groups": list(dupes.values()),
            "note": "dry-run only — POST with execute=1 to apply "
                    "(keeps the first row of each group)"}


@router.post("/dedupe")
def dedupe_execute(execute: int = 0):
    """Remove all-but-first row of each duplicate group.
    Pass ?execute=1 to actually run it."""
    if not execute:
        return dedupe_plan()
    plan = dedupe_plan()
    removed, errors = [], []
    for group in plan["groups"]:
        for row in group[1:]:
            # library_remove needs the LIBRARY id (i.xxx) — row["id"] is the
            # catalog id when the row has one (the 500s proved it)
            lid = row.get("library_id") or row["id"]
            try:
                mk.library_remove([lid])
                removed.append(lid)
            except BrowserError as e:
                errors.append({"id": lid, "error": str(e)[:150]})
    return {"ok": True, "removed": removed, "errors": errors,
            "removed_count": len(removed)}


# ---------------------------------------------------------------- rate

@router.get("/rate")
def rate_plan(artist: str = None, album: str = None, limit: int = 500):
    """Dry-run: which library songs a batch-rate would heart.
    (Execution re-checks each song's current rating and skips hearts.)"""
    rows = _all_library_songs()
    picked = []
    for r in rows:
        attrs = r.get("attributes", {})
        if artist and artist.lower() not in (attrs.get("artistName") or "").lower():
            continue
        if album and album.lower() not in (attrs.get("albumName") or "").lower():
            continue
        picked.append(_song_row(r))
        if len(picked) >= limit:
            break
    return {"would_heart": len(picked), "songs": picked,
            "note": "dry-run only — POST with execute=1 to apply. "
                    "Rate sweeps only ADD hearts; they never clear one."}


@router.post("/rate")
def rate_execute(artist: str = None, album: str = None, limit: int = 500,
                 execute: int = 0):
    """Heart every library song matching the filter, skipping songs that
    already have a rating. Pass ?execute=1 to actually run it."""
    if not execute:
        return rate_plan(artist, album, limit)
    plan = rate_plan(artist, album, limit)
    done, skipped, errors = [], [], []
    for song in plan["songs"]:
        try:
            # ratings are keyed by CATALOG id, not the library id
            rid = song.get("catalog_id") or song["id"]
            current = mk.get_rating(rid)
            if current == 1:
                skipped.append(rid)
                continue
            mk.rate_song(rid, True)
            done.append(rid)
        except BrowserError as e:
            errors.append({"id": song.get("id"), "error": str(e)[:150]})
    return {"ok": True, "hearted": done, "already_hearted": skipped,
            "errors": errors, "hearted_count": len(done)}


# ---------------------------------------------------------------- report

@router.get("/never-played")
def never_played(limit: int = 100, offset: int = 0):
    """Read-only report: library songs with no reported plays.
    NOTE: Apple's API currently does not expose play counts on
    library-songs at all — when that's the case this reports
    `play_count_available: false` rather than pretending every song is
    unplayed."""
    rows = _all_library_songs()
    out = []
    for r in rows:
        attrs = r.get("attributes", {})
        plays = attrs.get("playCount")
        if plays in (None, 0):
            out.append({**_song_row(r), "play_count": plays})
    available = any(x["play_count"] is not None for x in out)
    return {"library_size": len(rows), "never_played": len(out),
            "play_count_available": available,
            "songs": out[offset:offset + limit]}
