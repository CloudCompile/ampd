import fastapi
from fastapi import APIRouter, HTTPException

from .. import musickit as mk
from ..browser import BrowserError

router = APIRouter(prefix="/library", tags=["library"])


@router.get("/playlists")
def playlists():
    """All playlists in your library (id, name, track count)."""
    def extract(data):
        return [{
            "id": pl["id"],
            "name": pl.get("attributes", {}).get("name"),
            "track_count": (pl.get("attributes", {}).get("trackCount")),
        } for pl in data.get("data", [])]
    try:
        return {"playlists": mk.paginated("/v1/me/library/playlists?limit=100", extract)}
    except BrowserError as e:
        raise HTTPException(502, str(e))


@router.get("/playlists/{playlist_id}/tracks")
def playlist_tracks(playlist_id: str):
    """Every track of a library playlist (auto-paginated)."""
    try:
        return {"tracks": mk.playlist_tracks(playlist_id)}
    except BrowserError as e:
        raise HTTPException(502, str(e))


@router.get("/songs")
def library_songs(limit: int = 100, offset: int = 0):
    """Songs in your library (one page; use the pass-through for deep walks)."""
    try:
        data = mk.api_music(f"/v1/me/library/songs?limit={min(limit, 100)}&offset={offset}")
        return {"songs": [mk.song_row(t) for t in data.get("data", [])],
                "next": data.get("next")}
    except BrowserError as e:
        raise HTTPException(502, str(e))


@router.get("/recently-added")
def recently_added(limit: int = 25):
    """Most recently added library items (any kind)."""
    try:
        data = mk.api_music(f"/v1/me/library/recently-added?limit={min(limit, 100)}")
        return {"items": [mk.song_row(t) | {"type": t.get("type")}
                          for t in data.get("data", [])]}
    except BrowserError as e:
        raise HTTPException(502, str(e))


@router.get("/search-catalog")
def search_catalog(term: str, limit: int = 10):
    """Search the Apple Music catalog (songs)."""
    if not term:
        raise HTTPException(400, "term is required")
    try:
        data = mk.api_music(
            f"/v1/catalog/us/search?term={fastapi.encoders.jsonable_encoder(term)}"
            f"&limit={min(limit, 25)}&types=songs")
        songs = (data.get("results", {}).get("songs", {}).get("data", []))
        return {"songs": [mk.song_row(t) for t in songs]}
    except BrowserError as e:
        raise HTTPException(502, str(e))
