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
  digest        one walk -> dedupe + never-played summary (v0.6 automation)

The plan computations live in `tonearm/sweeps.py` so the scheduled digest
can reuse them without importing a router.
"""
from fastapi import APIRouter

from .. import musickit as mk
from .. import sweeps as sweeps_mod
from .. import webhooks
from ..browser import BrowserError
from ..config import config
from ..errors import ApiError
from ..models import (DedupePlan, DedupeReport, NeverPlayedPlan, RatePlan,
                      RateReport, SweepDigest)


def _guard():
    """Execution paths ONLY — the dry-run plans are pure reads and stay
    open. This was a real gap (execute bypassed the writes flag); the
    README's promise is /api/write/* mutations are 501 until
    TONEARM_ENABLE_WRITES=1."""
    if not config.enable_writes:
        raise ApiError(
            501, "writes_disabled",
            "batch sweeps mutate your library — they ship off like every "
            "other write. To enable, set TONEARM_ENABLE_WRITES=1 in the "
            "environment.")


router = APIRouter(prefix="/write/sweeps", tags=["sweeps (batch, dry-run default)"])


# ---------------------------------------------------------------- dedupe

@router.get("/dedupe", response_model=DedupePlan)
def dedupe_plan():
    """Dry-run: groups of duplicate library rows. Nothing is touched."""
    plan = sweeps_mod.dedupe_from_rows(sweeps_mod.all_library_songs())
    return {**plan, "note": "dry-run only — POST with execute=1 to apply "
                            "(keeps the first row of each group)"}


@router.post("/dedupe", response_model=DedupePlan | DedupeReport)
def dedupe_execute(execute: int = 0):
    """Remove all-but-first row of each duplicate group.
    Pass ?execute=1 to actually run it."""
    if not execute:
        return dedupe_plan()
    _guard()
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
    webhooks.emit(webhooks.LIBRARY_DEDUPED,
                  {"removed_count": len(removed), "removed": removed,
                   "errors": errors})
    return {"ok": True, "removed": removed, "errors": errors,
            "removed_count": len(removed)}


# ---------------------------------------------------------------- rate

@router.get("/rate", response_model=RatePlan)
def rate_plan(artist: str = None, album: str = None, limit: int = 500):
    """Dry-run: which library songs a batch-rate would heart.
    (Execution re-checks each song's current rating and skips hearts.)"""
    picked = sweeps_mod.rate_candidates_from_rows(
        sweeps_mod.all_library_songs(), artist=artist, album=album,
        limit=limit)
    return {"would_heart": len(picked), "songs": picked,
            "note": "dry-run only — POST with execute=1 to apply. "
                    "Rate sweeps only ADD hearts; they never clear one."}


@router.post("/rate", response_model=RatePlan | RateReport)
def rate_execute(artist: str = None, album: str = None, limit: int = 500,
                 execute: int = 0):
    """Heart every library song matching the filter, skipping songs that
    already have a rating. Pass ?execute=1 to actually run it."""
    if not execute:
        return rate_plan(artist, album, limit)
    _guard()
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
    webhooks.emit(webhooks.LIBRARY_RATED,
                  {"hearted_count": len(done), "hearted": done,
                   "already_hearted": skipped, "errors": errors})
    return {"ok": True, "hearted": done, "already_hearted": skipped,
            "errors": errors, "hearted_count": len(done)}


# ---------------------------------------------------------------- report

@router.get("/never-played", response_model=NeverPlayedPlan)
def never_played(limit: int = 100, offset: int = 0):
    """Read-only report: library songs with no reported plays.
    NOTE: Apple's API currently does not expose play counts on
    library-songs at all — when that's the case this reports
    `play_count_available: false` rather than pretending every song is
    unplayed."""
    return sweeps_mod.never_played_from_rows(
        sweeps_mod.all_library_songs(), limit=limit, offset=offset)


# ---------------------------------------------------------------- digest

@router.get("/digest", response_model=SweepDigest)
def digest():
    """Dry-run digest: dedupe + never-played from ONE library walk.
    The same payload is emitted as `sweep.digest` on the scheduled cadence
    (TONEARM_DIGEST_INTERVAL + TONEARM_WEBHOOKS=1)."""
    return sweeps_mod.build_digest()
