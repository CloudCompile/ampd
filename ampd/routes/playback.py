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


@router.get("/volume")
def get_volume():
    try:
        return {"volume": mk.playback_property("volume")}
    except BrowserError as e:
        raise HTTPException(502, str(e))


@router.post("/volume/{value}")
def set_volume(value: float):
    if not 0 <= value <= 1:
        raise HTTPException(400, "volume is 0.0 – 1.0")
    try:
        mk.set_playback_property("volume", value)
        return {"ok": True, "volume": value}
    except BrowserError as e:
        raise HTTPException(502, str(e))


@router.get("/settings")
def settings():
    """shuffle / repeat / volume in one shot."""
    try:
        return mk.playback_settings()
    except BrowserError as e:
        raise HTTPException(502, str(e))


@router.post("/shuffle/{mode}")
def shuffle(mode: str):
    if mode not in ("on", "off"):
        raise HTTPException(400, "shuffle is 'on' or 'off'")
    try:
        mk.set_playback_property("shuffle", mode)
        return {"ok": True, "shuffle": mode}
    except BrowserError as e:
        raise HTTPException(502, str(e))


@router.post("/repeat/{mode}")
def repeat(mode: int):
    # MusicKit repeat modes: 0 none, 1 one, 2 all
    if mode not in (0, 1, 2):
        raise HTTPException(400, "repeat is 0 (none), 1 (one), 2 (all)")
    try:
        mk.set_playback_property("repeat", mode)
        return {"ok": True, "repeat": mode}
    except BrowserError as e:
        raise HTTPException(502, str(e))


@router.post("/play-collection")
def play_collection(kind: str, id: str):
    """Queue a whole album/playlist/station and play it.
    kind: album | playlist | station  (catalog ids)"""
    if kind not in ("album", "playlist", "station"):
        raise HTTPException(400, "kind must be album, playlist, or station")
    try:
        mk.play_collection(kind, id)
        return {"ok": True}
    except BrowserError as e:
        raise HTTPException(502, str(e))
