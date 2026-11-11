from fastapi import APIRouter, HTTPException

from .. import musickit as mk
from ..browser import BrowserError
from ..config import config

router = APIRouter(prefix="/favorites", tags=["favorites"])

_fav_pid_cache = None


def favorites_playlist_id() -> str:
    """Locate the auto-generated 'Favorite Songs' playlist id (cached)."""
    global _fav_pid_cache
    if _fav_pid_cache:
        return _fav_pid_cache
    pid = mk.find_library_playlist(config.favorites_playlist_name)
    if not pid:
        raise HTTPException(404, f"no library playlist named {config.favorites_playlist_name!r}")
    _fav_pid_cache = pid
    return pid


def _writes_disabled():
    if not config.enable_writes:
        raise HTTPException(
            501,
            "Write operations are disabled. ampD ships with mutations off so it can "
            "never touch your library by accident. To enable them, set "
            "AMPD_ENABLE_WRITES=1 in the environment.")


@router.get("")
def list_favorites():
    """Every song in your Favorite Songs playlist (auto-paginated, with art)."""
    try:
        tracks = mk.playlist_tracks(favorites_playlist_id())
        return {"count": len(tracks), "tracks": tracks}
    except BrowserError as e:
        raise HTTPException(502, str(e))


@router.post("/{song_id}")
def favorite(song_id: str):
    """Favorite a catalog song. STUB — disabled by default."""
    _writes_disabled()


@router.delete("/{song_id}")
def unfavorite(song_id: str):
    """Unfavorite a song. STUB — disabled by default.

    When enabled, ampD tries the catalog-keyed call first, then the
    library-keyed one (some library tracks are keyed by their library id —
    discovered while trimming a real account).
    """
    _writes_disabled()
