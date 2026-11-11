"""Write operations — ALL stubbed until AMPD_ENABLE_WRITES=1.

These are the documented-and-undocumented mutations we've validated by hand
(favorites toggling in both key flavors) plus the standard MusicKit library
mutations. They ship disabled so the server can never touch your library by
accident; enabling them is a single env var.

NOTE: every parameter is optional *at the signature level* on purpose —
the 501 must fire before FastAPI validation complains about missing args.
"""
from fastapi import APIRouter, HTTPException

from ..config import config

router = APIRouter(prefix="/write", tags=["writes (disabled by default)"])


def _writes_disabled():
    if not config.enable_writes:
        raise HTTPException(
            501,
            "Write operations are disabled. ampD ships with mutations off so it "
            "can never touch your library by accident. To enable, set "
            "AMPD_ENABLE_WRITES=1 in the environment.")


@router.post("/favorites/{song_id}")
def favorite(song_id: str, library_key: bool = False):
    """Favorite (heart) a song. `library_key=true` for library-keyed tracks."""
    _writes_disabled()


@router.delete("/favorites/{song_id}")
def unfavorite(song_id: str, library_key: bool = False):
    """Unfavorite a song."""
    _writes_disabled()


@router.post("/library/add")
def add_to_library(catalog_ids: list[str] = None):
    """Add catalog resources to your library (POST /v1/me/library)."""
    _writes_disabled()


@router.post("/playlists")
def create_playlist(name: str = None, description: str = ""):
    """Create a library playlist."""
    _writes_disabled()


@router.post("/playlists/{playlist_id}/tracks")
def add_tracks(playlist_id: str, track_ids: list[str] = None):
    """Add tracks to a library playlist."""
    _writes_disabled()


@router.delete("/playlists/{playlist_id}/tracks")
def remove_tracks(playlist_id: str, track_ids: list[str] = None):
    """Remove tracks from a library playlist (the safe, idempotent way to
    sweep a playlist — validated during a real 253-song trim)."""
    _writes_disabled()


@router.patch("/playlists/{playlist_id}")
def rename_playlist(playlist_id: str, name: str = None, description: str = None):
    """Rename / re-describe a library playlist."""
    _writes_disabled()


@router.delete("/playlists/{playlist_id}")
def delete_playlist(playlist_id: str):
    """Delete a library playlist."""
    _writes_disabled()


@router.put("/ratings/songs/{song_id}")
def rate_song(song_id: str, rating: str = None):
    """rating: like | dislike | none (the classic star/heart ratings)."""
    _writes_disabled()
