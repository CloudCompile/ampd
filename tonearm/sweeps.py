"""Batch library sweep planning — pure, route-free (v0.6 digest reuse).

The route layer (`routes/sweeps.py`) and the scheduled digest both need the
same plans. Keeping the computations here means the digest never imports a
router, and both surfaces stay net-zero: every function in this module is a
READ unless a route explicitly executes the plan.

Design rule (learned the hard way): a song's heart is its rating, and
removals are irreversible. Nothing here mutates; execution lives in the
route with the writes guard.
"""
import time

from . import musickit as mk


def all_library_songs():
    """One complete walk of /v1/me/library/songs (paginated, raw rows)."""
    return mk.paginated("/v1/me/library/songs?limit=100",
                        lambda d: d.get("data", []))


def row_identity(row):
    """Group key: catalog id when known, else name+artist+duration."""
    attrs = row.get("attributes", {})
    catalog = (attrs.get("playParams") or {}).get("catalogId")
    if catalog:
        return f"cat:{catalog}", catalog
    dur = attrs.get("durationInMillis")
    return (f"nd:{(attrs.get('name') or '').lower()}|"
            f"{(attrs.get('artistName') or '').lower()}|{dur}"), None


def song_row(row):
    return mk.item_row(row)


def dedupe_from_rows(rows):
    """Group duplicate library rows. The first row of each group is kept."""
    groups = {}
    for r in rows:
        key, _ = row_identity(r)
        groups.setdefault(key, []).append(r)
    dupes = {k: [song_row(x) for x in v]
             for k, v in groups.items() if len(v) > 1}
    return {"library_size": len(rows),
            "duplicate_groups": len(dupes),
            "removable_rows": sum(len(v) - 1 for v in dupes.values()),
            "groups": list(dupes.values())}


def rate_candidates_from_rows(rows, artist=None, album=None, limit=500):
    """Rows a batch-rate would heart (first `limit` matches)."""
    picked = []
    for r in rows:
        attrs = r.get("attributes", {})
        if artist and artist.lower() not in (attrs.get("artistName") or "").lower():
            continue
        if album and album.lower() not in (attrs.get("albumName") or "").lower():
            continue
        picked.append(song_row(r))
        if len(picked) >= limit:
            break
    return picked


def never_played_from_rows(rows, limit=100, offset=0):
    """Read-only report of rows Apple reports no plays for. Play counts are
    absent on many library rows — say so instead of pretending every song
    is unplayed."""
    out = []
    for r in rows:
        attrs = r.get("attributes", {})
        plays = attrs.get("playCount")
        if plays in (None, 0):
            out.append({**song_row(r), "play_count": plays})
    available = any(x["play_count"] is not None for x in out)
    return {"library_size": len(rows), "never_played": len(out),
            "play_count_available": available,
            "songs": out[offset:offset + limit]}


def build_digest(sample=10):
    """One walk -> the scheduled digest payload (dedupe + never-played).
    Samples are capped so a 9k-song library never becomes a megabyte event."""
    rows = all_library_songs()
    dedupe = dedupe_from_rows(rows)
    never = never_played_from_rows(rows, limit=sample, offset=0)
    return {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "library_size": len(rows),
        "duplicate_groups": dedupe["duplicate_groups"],
        "removable_rows": dedupe["removable_rows"],
        "never_played": never["never_played"],
        "play_count_available": never["play_count_available"],
        "sample_duplicates": dedupe["groups"][:min(sample, 5)],
        "sample_never_played": never["songs"],
    }
