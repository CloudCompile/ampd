from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from io import BytesIO
from urllib.request import urlopen

from PIL import Image, ImageEnhance, ImageFilter, ImageOps

from .. import musickit as mk
from ..browser import BrowserError
from ..models import (NowPlaying, Ok, OkPlaylist, OkRating, OkRepeat,
                      OkShuffle, OkStatus, OkVolume, PlaybackSettings, Queue,
                      QueueItem, QueueReorder, VolumeState)

router = APIRouter(prefix="/playback", tags=["playback"])

_background_cache: dict[str, bytes] = {}


@router.get("/artwork-background", include_in_schema=False)
def artwork_background():
    """Return one cached, darkened/blurred 64x32 version of the current
    artwork for the Tidbyt background. The cache key is the artwork URL:
    one image generation per track/art change, never one per display frame."""
    try:
        now = mk.now_playing()
        url = now.get("artworkUrl") or ""
        if not url:
            raise HTTPException(404, "no artwork")
        url = url.replace("{w}", "600").replace("{h}", "600")
        if url not in _background_cache:
            with urlopen(url, timeout=15) as r:
                source = r.read(2_000_000)
            image = Image.open(BytesIO(source)).convert("RGB")
            tile = ImageOps.fit(image, (24, 24), method=Image.Resampling.LANCZOS)
            image = ImageOps.fit(image, (64, 32), method=Image.Resampling.LANCZOS)
            image = image.filter(ImageFilter.GaussianBlur(radius=4))
            image = ImageEnhance.Brightness(image).enhance(0.38)
            # One device-side image buffer: the clear 24x24 artwork tile is
            # composited into the right-hand position server-side. Lyrics
            # mode simply paints over this tile; no second online_image
            # decoder/buffer is needed on the ESP32.
            image.paste(tile, (40, 4))
            out = BytesIO()
            image.save(out, format="JPEG", quality=78, optimize=True)
            _background_cache[url] = out.getvalue()
            # Keep only the current cover; the device asks for a replacement
            # on track change, so this cannot become a library cache.
            if len(_background_cache) > 2:
                for old in list(_background_cache)[:-1]:
                    del _background_cache[old]
        return Response(_background_cache[url], media_type="image/jpeg",
                        headers={"Cache-Control": "public, max-age=3600"})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(502, f"artwork background unavailable: {e}")

# NOTE: specific routes MUST be declared before the generic /{command} route.

@router.get("/now-playing", response_model=NowPlaying)
def now_playing():
    try:
        return mk.now_playing()
    except BrowserError as e:
        raise HTTPException(502, str(e))


@router.get("/queue", response_model=Queue)
def queue():
    """The current queue (also pushed by the SSE stream — prefer the
    stream; this is the one-shot read)."""
    try:
        return {"items": mk.queue()}
    except BrowserError as e:
        raise HTTPException(502, str(e))


@router.put("/queue", response_model=Ok)
def queue_reorder(body: QueueReorder):
    """Reorder the queue: send the FULL ordered list of item ids (#87 —
    whole-list PUT semantics, last write wins, no deltas). The playhead
    stays on the same track at its new index. Best-effort like every
    transport op: MusicKit has no public reorder, so the queue is rebuilt
    and the playhead is moved back onto the same track."""
    try:
        mk.queue_reorder(body.ids)
        return {"ok": True}
    except BrowserError as e:
        if "no such queue item" in str(e).lower():
            raise HTTPException(404, str(e))
        raise HTTPException(502, str(e))


@router.get("/volume", response_model=VolumeState)
def get_volume():
    try:
        return {"volume": mk.playback_property("volume")}
    except BrowserError as e:
        raise HTTPException(502, str(e))


@router.post("/volume/{value}", response_model=OkVolume)
def set_volume(value: float):
    if not 0 <= value <= 1:
        raise HTTPException(400, "volume is 0.0 – 1.0")
    try:
        mk.set_playback_property("volume", value)
        return {"ok": True, "volume": value}
    except BrowserError as e:
        raise HTTPException(502, str(e))


@router.get("/settings", response_model=PlaybackSettings)
def settings():
    """shuffle / repeat / volume / playing state in one shot."""
    try:
        return mk.playback_settings()
    except BrowserError as e:
        raise HTTPException(502, str(e))


@router.post("/shuffle/{mode}", response_model=OkShuffle)
def shuffle(mode: str):
    if mode not in ("on", "off"):
        raise HTTPException(400, "shuffle is 'on' or 'off'")
    try:
        mk.set_playback_property("shuffle", mode)
        return {"ok": True, "shuffle": mode}
    except BrowserError as e:
        raise HTTPException(502, str(e))


@router.post("/repeat/{mode}", response_model=OkRepeat)
def repeat(mode: int):
    # MusicKit repeat modes: 0 none, 1 one, 2 all
    if mode not in (0, 1, 2):
        raise HTTPException(400, "repeat is 0 (none), 1 (one), 2 (all)")
    try:
        mk.set_playback_property("repeat", mode)
        return {"ok": True, "repeat": mode}
    except BrowserError as e:
        raise HTTPException(502, str(e))


@router.post("/play-song/{catalog_id}", response_model=Ok)
def play_song(catalog_id: str):
    """Start playing a catalog song by id (clears the queue)."""
    try:
        mk.play_song(catalog_id)
        return {"ok": True}
    except BrowserError as e:
        raise HTTPException(502, str(e))


@router.post("/play-collection", response_model=Ok)
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


@router.post("/play-next", response_model=Ok)
def play_next(catalog_id: str):
    """Insert a catalog song to play next."""
    try:
        mk.queue_add(catalog_id, play_next=True)
        return {"ok": True}
    except BrowserError as e:
        raise HTTPException(502, str(e))


@router.post("/play-later", response_model=Ok)
def play_later(catalog_id: str):
    """Append a catalog song to play later."""
    try:
        mk.queue_add(catalog_id, play_next=False)
        return {"ok": True}
    except BrowserError as e:
        raise HTTPException(502, str(e))



@router.post("/back", response_model=Ok)
def back(threshold_ms: int = 10000):
    """Hardware-button 'back' (the Tidbyt's triple-tap): past the
    threshold (default 10s), 'back' means RESTART this song; before it,
    previous track. Additive route, not a change to /previous — the
    freeze's allowlist is additions only."""
    if not 0 <= threshold_ms <= 600000:
        raise HTTPException(400, "threshold_ms out of range")
    try:
        result = mk.playback_back(threshold_ms) or {}
        if result.get("warn"):
            raise HTTPException(502, result["warn"])
        return {"ok": True, **result}
    except BrowserError as e:
        raise HTTPException(502, str(e))

@router.post("/{command}", response_model=Ok)
def command(command: str):
    """play | pause | toggle | next | previous."""
    if command not in ("play", "pause", "toggle", "next", "previous"):
        raise HTTPException(404, f"unknown playback command {command!r}")
    try:
        mk.playback_command(command)
        return {"ok": True}
    except BrowserError as e:
        raise HTTPException(502, str(e))


@router.post("/back", response_model=Ok)
def back(threshold_ms: int = 10000):
    """Hardware-button 'back' (the Tidbyt's triple-tap): past the
    threshold (default 10s), 'back' means RESTART this song; before it,
    previous track. Additive route, not a change to /previous — the
    freeze's allowlist is additions only."""
    if not 0 <= threshold_ms <= 600000:
        raise HTTPException(400, "threshold_ms out of range")
    try:
        result = mk.playback_back(threshold_ms) or {}
        if result.get("warn"):
            raise HTTPException(502, result["warn"])
        return {"ok": True, **result}
    except BrowserError as e:
        raise HTTPException(502, str(e))
