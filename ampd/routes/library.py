"""Generic library surface: every `me/library` resource type, one router.

GET /api/library/{resource}                      list (paginated, searchable)
GET /api/library/{resource}/{id}                 one item (with relationships)
GET /api/library/{resource}/{id}/{relationship}  e.g. albums/{id}/tracks
GET /api/library/search?term=                    library-wide search
GET /api/library/recently-added                  most recent additions
"""
import time
import urllib.parse

from fastapi import APIRouter, HTTPException

from .. import musickit as mk
from .. import exporter
from ..browser import BrowserError
from ..store import StoreDisabled, store

router = APIRouter(prefix="/library", tags=["library"])

RESOURCES = {"songs", "albums", "artists", "playlists", "music-videos"}
# NOTE: no "stations" — Apple's library API rejects it ("Unknown library
# resource type"); stations exist only in the catalog.


def _path(resource, limit, offset, term=None, extend=None):
    if resource not in RESOURCES:
        raise HTTPException(404, f"unknown library resource {resource!r}. "
                                 f"Valid: {sorted(RESOURCES)}")
    q = f"limit={min(limit, 100)}&offset={offset}"
    if term:
        q += "&term=" + urllib.parse.quote(term)
    if extend:
        q += "&extend=" + urllib.parse.quote(extend)
    return f"/v1/me/library/{resource}?{q}"


@router.get("/playlists/{playlist_id}/tracks")
def playlist_tracks(playlist_id: str):
    """Every track of a library playlist (auto-paginated to the end).
    NOTE: declared before the generic routes so it wins the match."""
    try:
        return {"tracks": mk.playlist_tracks(playlist_id)}
    except BrowserError as e:
        raise HTTPException(502, str(e))


@router.get("/export")
def export_library(songs_limit: int = 100000):
    """Full library dump as JSON — every song + every playlist (with track
    ids). Slow by design: walks the entire library (~100 s per 9k songs).
    Point a cron at this for backups; the output is a complete restore
    reference (ids) if the library is ever lost."""
    try:
        return exporter.build_export(mk, songs_limit=songs_limit)
    except BrowserError as e:
        raise HTTPException(502, str(e))


@router.get("/diff")
def library_diff(since: float = 0.0, what: str = "all",
                 limit: int = 100, offset: int = 0):
    """What changed in your library since a unix timestamp.

    Apple has no "changed since" filter — this diff is OURS, computed from
    the local store's watermark columns (first_seen / last_seen /
    last_changed) across snapshot walks. So:
      * `since=0` (default) -> the whole library as `added`
      * removals become visible on the FIRST walk AFTER they happen
      * `what` filters: added | updated | removed | all
    """
    if since > time.time():
        raise HTTPException(400, "since is in the future")
    try:
        if what == "added":
            return {"added": store.library_added_since(since, limit, offset)}
        if what == "updated":
            return {"updated": store.library_updated_since(since, limit, offset)}
        if what == "removed":
            return {"removed": store.library_removed_since(since, limit, offset)}
        return {"added": store.library_added_since(since, limit, offset),
                "updated": store.library_updated_since(since, limit, offset),
                "removed": store.library_removed_since(since, limit, offset),
                "walk": store.get_cursor("library.walk")}
    except StoreDisabled as e:
        raise HTTPException(501, str(e))


def _path(resource, limit, offset, term=None, extend=None):
    if resource not in RESOURCES:
        raise HTTPException(404, f"unknown library resource {resource!r}. "
                                 f"Valid: {sorted(RESOURCES)}")
    q = f"limit={min(limit, 100)}&offset={offset}"
    if term:
        q += "&term=" + urllib.parse.quote(term)
    if extend:
        q += "&extend=" + urllib.parse.quote(extend)
    return f"/v1/me/library/{resource}?{q}"


@router.get("/search")
def library_search(term: str, limit: int = 25):
    """Search YOUR library across songs/albums/artists/playlists."""
    if not term:
        raise HTTPException(400, "term is required")
    try:
        data = mk.api_music(
            f"/v1/me/library/search?term={urllib.parse.quote(term)}"
            f"&types=library-songs,library-albums,library-artists,library-playlists"
            f"&limit={min(limit, 25)}")
        out = {}
        for kind, group in (data.get("results", {}) or {}).items():
            if isinstance(group, dict) and group.get("data"):
                out[kind.replace("library-", "")] = [mk.item_row(t) for t in group["data"]]
        return out
    except BrowserError as e:
        raise HTTPException(502, str(e))


@router.get("/recently-added")
def recently_added(limit: int = 25):
    """Most recently added library items (any kind)."""
    try:
        data = mk.api_music(f"/v1/me/library/recently-added?limit={min(limit, 100)}")
        return {"items": [mk.item_row(t) for t in data.get("data", [])]}
    except BrowserError as e:
        raise HTTPException(502, str(e))


@router.get("/{resource}")
def list_resource(resource: str, limit: int = 100, offset: int = 0,
                  term: str = None, extend: str = None):
    """List any library resource, fully paginated by the caller."""
    try:
        data = mk.api_music(_path(resource, limit, offset, term, extend))
        items = [mk.item_row(t) for t in data.get("data", [])]
        return {"items": items, "count": len(items),
                "next_offset": offset + len(items) if data.get("next") else None}
    except BrowserError as e:
        raise HTTPException(502, str(e))


@router.get("/{resource}/{resource_id}")
def get_resource(resource: str, resource_id: str):
    """One library item, with its relationships (e.g. an album's track list)."""
    try:
        data = mk.api_music(f"/v1/me/library/{resource}/{resource_id}")
        items = data.get("data", [])
        if not items:
            raise HTTPException(404, "not found in your library")
        out = mk.item_row(items[0])
        rels = items[0].get("relationships", {})
        out["relationships"] = {
            name: {"items": [mk.item_row(x) for x in rel.get("data", [])]}
            for name, rel in rels.items()
        }
        return out
    except BrowserError as e:
        raise HTTPException(502, str(e))


@router.get("/{resource}/{resource_id}/{relationship}")
def get_relationship(resource: str, resource_id: str, relationship: str,
                     limit: int = 100, offset: int = 0):
    """A relationship collection, e.g. /library/albums/{id}/tracks."""
    try:
        data = mk.api_music(
            f"/v1/me/library/{resource}/{resource_id}/{relationship}"
            f"?limit={min(limit, 100)}&offset={offset}")
        return {"items": [mk.item_row(t) for t in data.get("data", [])],
                "next": data.get("next")}
    except BrowserError as e:
        raise HTTPException(502, str(e))
