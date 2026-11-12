"""Write operations — ALL guarded behind AMPD_ENABLE_WRITES=1.

Implementation notes from live validation against a real account:
  * favorites: two key flavors — catalog songs use ids[songs], some library
    tracks only respond to ids[library-songs]. A wrong-key DELETE returns
    204 and does NOTHING, so callers should verify (GET /api/favorites).
  * ratings: PUT value 1 = like; DELETE clears. Dislike is accepted but
    stores as 1 — not exposed.
  * playlist track removal AND reorder share one call: PUT the full
    ordered library-id list (DELETE .../tracks always 400s).
  * adding a catalog song to a library playlist auto-adds it to the library.
  * library add is 202-async; give Apple a beat before verifying.
"""
from fastapi import APIRouter, HTTPException

from .. import musickit as mk
from .. import restore as restore_mod
from ..browser import BrowserError
from ..config import config


def _norm(s):
    return (s or "").strip().lower()

router = APIRouter(prefix="/write", tags=["writes (disabled by default)"])


def _guard():
    if not config.enable_writes:
        raise HTTPException(
            501,
            "Write operations are disabled. ampD ships with mutations off so it "
            "can never touch your library by accident. To enable, set "
            "AMPD_ENABLE_WRITES=1 in the environment.")


# ---------------------------------------------------------------- favorites

@router.post("/favorites/{song_id}")
def favorite(song_id: str, library_key: bool = False):
    """Favorite (heart) a song. `library_key=true` for library-keyed tracks."""
    _guard()
    try:
        mk.set_favorite("library" if library_key else "catalog", song_id, True)
        return {"ok": True}
    except BrowserError as e:
        raise HTTPException(502, str(e))


@router.delete("/favorites/{song_id}")
def unfavorite(song_id: str, library_key: bool = False):
    """Unfavorite a song. Verify with GET /api/favorites — a wrong-key delete
    returns success without doing anything."""
    _guard()
    try:
        mk.set_favorite("library" if library_key else "catalog", song_id, False)
        return {"ok": True}
    except BrowserError as e:
        raise HTTPException(502, str(e))


# ---------------------------------------------------------------- ratings

@router.get("/ratings/songs/{song_id}")
def get_rating(song_id: str, fresh: bool = False):
    """Current rating of a song: null = none, 1 = like.
    Ratings lag server-side after a mutation; `?fresh=1` bypasses cache."""
    _guard()
    try:
        return {"song_id": song_id, "value": mk.get_rating(song_id, fresh=fresh)}
    except BrowserError as e:
        raise HTTPException(502, str(e))


@router.put("/ratings/songs/{song_id}")
def rate_song(song_id: str, rating: str = None):
    """rating: 'like' or 'none'."""
    _guard()
    if rating not in ("like", "none"):
        raise HTTPException(400, "rating must be 'like' or 'none' (dislike is "
                                 "accepted by Apple but stores as like — not exposed)")
    try:
        mk.rate_song(song_id, True if rating == "like" else None)
        return {"ok": True, "rating": rating}
    except BrowserError as e:
        raise HTTPException(502, str(e))


# ---------------------------------------------------------------- library

@router.post("/library/add")
def add_to_library(catalog_ids: list[str] = None):
    """Add catalog songs to your library. Body is a bare JSON array of
    catalog song ids. NOTE: 202-accepted (async on Apple's side); the
    songs appear in the library a moment later."""
    _guard()
    if not catalog_ids:
        raise HTTPException(400, "catalog_ids is required")
    try:
        status = mk.library_add(catalog_ids)
        return {"ok": True, "status": status,
                "note": "accepted asynchronously — verify via /api/library/songs"}
    except BrowserError as e:
        raise HTTPException(502, str(e))


@router.delete("/library/{library_song_id}")
def remove_from_library(library_song_id: str):
    """Remove a song from your library by its library id (i.XXX).
    This is NOT the same as unfavoriting. Destructive — no undo."""
    _guard()
    try:
        mk.library_remove([library_song_id])
        return {"ok": True}
    except BrowserError as e:
        raise HTTPException(502, str(e))


@router.post("/library/add-albums")
def add_albums_to_library(catalog_album_ids: list[str] = None):
    """Add catalog albums (all their tracks) to your library.
    Body: bare JSON array of catalog album ids. 202-async."""
    _guard()
    if not catalog_album_ids:
        raise HTTPException(400, "catalog_album_ids is required")
    try:
        status = mk.library_add_albums(catalog_album_ids)
        return {"ok": True, "status": status,
                "note": "accepted asynchronously — verify via /api/library/albums"}
    except BrowserError as e:
        raise HTTPException(502, str(e))


@router.delete("/library/albums/{library_album_id}")
def remove_album_from_library(library_album_id: str):
    """Remove a whole library album (l.XXX) — all its songs go too.
    Destructive — no undo."""
    _guard()
    try:
        mk.library_remove_album(library_album_id)
        return {"ok": True}
    except BrowserError as e:
        raise HTTPException(502, str(e))


# ---------------------------------------------------------------- playlists

@router.post("/playlists")
def create_playlist(name: str = None, description: str = ""):
    """Create a library playlist. Returns the new playlist id."""
    _guard()
    if not name:
        raise HTTPException(400, "name is required")
    try:
        return {"ok": True, "playlist_id": mk.playlist_create(name, description)}
    except BrowserError as e:
        raise HTTPException(502, str(e))


@router.post("/playlists/{playlist_id}/tracks")
def add_tracks(playlist_id: str, track_ids: list[str] = None):
    """Append catalog songs to a playlist (auto-adds them to the library).
    Body is a bare JSON array of catalog song ids."""
    _guard()
    if not track_ids:
        raise HTTPException(400, "track_ids is required")
    try:
        mk.playlist_add_tracks(playlist_id, track_ids)
        return {"ok": True}
    except BrowserError as e:
        raise HTTPException(502, str(e))


@router.put("/playlists/{playlist_id}/tracks")
def set_tracks(playlist_id: str, ordered_library_ids: list[str] = None):
    """REPLACE the track list, in order. Body is a bare JSON array of
    library-songs ids. This is both reorder and removal: send the full
    list minus any song you want gone.
    e.g.  curl -X PUT -d '["i.abc","i.def"]' /api/write/playlists/{pid}/tracks"""
    _guard()
    if ordered_library_ids is None:
        raise HTTPException(400, "ordered_library_ids is required")
    try:
        mk.playlist_set_tracks(playlist_id, ordered_library_ids)
        return {"ok": True}
    except BrowserError as e:
        raise HTTPException(502, str(e))


@router.patch("/playlists/{playlist_id}")
def rename_playlist(playlist_id: str, name: str = None, description: str = None):
    """Rename / re-describe a library playlist."""
    _guard()
    if name is None and description is None:
        raise HTTPException(400, "name and/or description required")
    try:
        mk.playlist_rename(playlist_id, name, description)
        return {"ok": True}
    except BrowserError as e:
        raise HTTPException(502, str(e))


@router.delete("/playlists/{playlist_id}")
def delete_playlist(playlist_id: str):
    """Delete a library playlist. Destructive — no undo."""
    _guard()
    try:
        mk.playlist_delete(playlist_id)
        return {"ok": True}
    except BrowserError as e:
        raise HTTPException(502, str(e))


# ---------------------------------------------------------------- restore

@router.post("/restore")
def restore(source: dict = None, execute: int = 0, match_budget: int = 2000):
    """Restore playlists from a /api/library/export JSON body.

    DRY-RUN BY DEFAULT: returns the plan (per playlist: exists/create,
    per track: catalog-id / name-match / unmatched-with-reason).
    `?execute=1` runs it: creates missing playlists, adds tracks, verifies
    counts with bounded retries (Apple's applies are async).

    The unmatched report is the contract: nothing is ever dropped silently.
    """
    _guard()
    if not source or not isinstance(source.get("playlists"), list):
        raise HTTPException(400, "body must be a /api/library/export JSON "
                                 "shape (needs a 'playlists' array)")
    if execute:
        _plan = restore(source, execute=0, match_budget=match_budget)
        if not isinstance(_plan, dict) or "playlists" not in _plan:
            raise HTTPException(502, "plan rebuild failed")
        try:
            report = restore_mod.execute_plan(_plan, mk)
            return {"ok": True, "plan_totals": _plan["totals"],
                    "report": report}
        except BrowserError as e:
            raise HTTPException(502, str(e))

    def existing_lookup(name):
        return _existing.get(_norm(name))

    def catalog_lookup(name, artist):
        term = " ".join(x for x in (name, artist) if x)
        if not term:
            return None
        try:
            import urllib.parse
            data = mk.api_music(
                f"/v1/catalog/us/search?term={urllib.parse.quote(term)}"
                f"&types=songs&limit=5")
            songs = (data.get("results", {}).get("songs", {}) or {}).get("data", [])
            for s in songs:
                a = s.get("attributes", {})
                if (_norm(a.get("name")) == _norm(name)
                        and _norm(a.get("artistName")) == _norm(artist)):
                    return s["id"]
            return None
        except BrowserError:
            return None

    # ONE walk of the playlist names (find-per-name would re-walk per
    # playlist — 50 playlists must not cost 50 full walks)
    try:
        pls = mk.paginated("/v1/me/library/playlists?limit=100",
                           lambda d: d.get("data", []), fresh=True)
        _existing = {(p.get("attributes", {}) or {}).get("name") or "": p["id"]
                     for p in pls}
    except BrowserError as e:
        raise HTTPException(502, str(e))

    try:
        return restore_mod.build_plan(source, existing_lookup,
                                      catalog_lookup, match_budget)
    except BrowserError as e:
        raise HTTPException(502, str(e))
