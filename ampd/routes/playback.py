from fastapi import APIRouter, HTTPException

from .. import musickit as mk
from ..browser import BrowserError

router = APIRouter(prefix="/playback", tags=["playback"])


@router.get("/now-playing")
def now_playing():
    try:
        return mk.now_playing()
    except BrowserError as e:
        raise HTTPException(502, str(e))


@router.post("/{command}")
def command(command: str):
    """play | pause | toggle | next | previous."""
    if command not in ("play", "pause", "toggle", "next", "previous"):
        raise HTTPException(404, f"unknown playback command {command!r}")
    try:
        mk.playback_command(command)
        return {"ok": True}
    except BrowserError as e:
        raise HTTPException(502, str(e))


@router.post("/play-song/{catalog_id}")
def play_song(catalog_id: str):
    """Start playing a catalog song by id (clears the queue)."""
    try:
        mk.play_song(catalog_id)
        return {"ok": True}
    except BrowserError as e:
        raise HTTPException(502, str(e))


@router.get("/queue")
def queue():
    try:
        return {"items": mk.queue()}
    except BrowserError as e:
        raise HTTPException(502, str(e))
