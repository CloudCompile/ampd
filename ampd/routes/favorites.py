from fastapi import APIRouter, HTTPException

from .. import musickit as mk
from ..browser import BrowserError
from .writes import router as writes  # noqa: F401  (write ops live in /write)

router = APIRouter(prefix="/favorites", tags=["favorites"])

_fav_pid_cache = None


def favorites_playlist_id() -> str:
    """Locate the auto-generated 'Favorite Songs' playlist id (cached)."""
    global _fav_pid_cache
    if _fav_pid_cache:
        return _fav_pid_cache
    pid = mk.find_library_playlist(mk.config.favorites_playlist_name)
    if not pid:
        raise HTTPException(404, f"no library playlist named "
                                 f"{mk.config.favorites_playlist_name!r}")
    _fav_pid_cache = pid
    return pid


@router.get("")
def list_favorites():
    """Every song in your Favorite Songs playlist (auto-paginated, with art)."""
    try:
        tracks = mk.playlist_tracks(favorites_playlist_id())
        return {"count": len(tracks), "tracks": tracks}
    except BrowserError as e:
        raise HTTPException(502, str(e))
