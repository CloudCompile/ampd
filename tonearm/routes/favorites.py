from fastapi import APIRouter, HTTPException

from .. import musickit as mk
from ..browser import BrowserError
from ..config import config
from ..models import Favorites
from .writes import router as writes  # noqa: F401  (write ops live in /write)

router = APIRouter(prefix="/favorites", tags=["favorites"])

_fav_pid_cache = None


def favorites_playlist_id(fresh: bool = False) -> str:
    """Locate the auto-generated 'Favorite Songs' playlist id (cached).
    `fresh` re-resolves it — the cached id can go stale if the playlist is
    renamed/deleted out from under us (Apple's auto-playlist is theirs)."""
    global _fav_pid_cache
    if _fav_pid_cache and not fresh:
        return _fav_pid_cache
    pid = mk.find_library_playlist(config.favorites_playlist_name, fresh=fresh)
    if not pid:
        _fav_pid_cache = None
        raise HTTPException(404, f"no library playlist named "
                                 f"{config.favorites_playlist_name!r}")
    _fav_pid_cache = pid
    return pid


@router.get("", response_model=Favorites)
def list_favorites(fresh: bool = False):
    """Every song in your Favorite Songs playlist (auto-paginated, with art).
    Also returns `playlist_id` so clients can browse it like any playlist.
    Apple's favorites auto-sync lags ~60s+; `?fresh=1` bypasses the read
    cache when you need the live state."""
    try:
        pid = favorites_playlist_id(fresh=fresh)
        tracks = mk.playlist_tracks(pid, fresh=fresh)
        return {"count": len(tracks), "playlist_id": pid, "tracks": tracks}
    except BrowserError as e:
        raise HTTPException(502, str(e))
