"""OBS overlay endpoints (v0.5 #94) — now-playing for streamers.

GET /api/overlay/now-playing.json   typed payload (OverlayNowPlaying model)
GET /api/overlay/now-playing.txt    text line for OBS's Text (GDI+) source

Both serve from the SSE stream's LAST EMITTED STATE (`stream.last_snapshot`)
— zero extra Chrome evals: the overlay piggybacks on data the stream already
fetched for its connected clients. If nothing has played yet (fresh boot,
no SSE client), the payload is honest nulls rather than a made-up state.

OBS setup (browser source): point it at the .json URL with
`custom headers -> Authorization: Bearer <AMPD_API_KEY>` when a key is set.
For a plain text source, poll the .txt URL the same way (OBS's Text source
has no headers — put the overlay behind no-key, or front it with a proxy
that injects them).
"""
from fastapi import APIRouter, Query
from fastapi.responses import PlainTextResponse

from ..models import OverlayNowPlaying
from .stream import last_snapshot

router = APIRouter(prefix="/overlay", tags=["overlay"])

DEFAULT_TEXT = "{title} — {artist}"


def _payload():
    snap = last_snapshot()
    # only these keys, in the model's shape — extra hook fields (seq, ts,
    # ev, ...) are stream plumbing, not overlay contract
    return {k: snap.get(k) for k in (
        "isPlaying", "state", "title", "artist", "album", "id",
        "durationMs", "elapsedMs", "progress", "volume", "shuffle",
        "repeat", "artworkUrl")}


@router.get("/now-playing.json", response_model=OverlayNowPlaying)
def now_playing_json():
    """Now-playing as JSON — for OBS browser sources and bots."""
    return _payload()


@router.get("/now-playing.txt", response_class=PlainTextResponse,
            response_model=None)
def now_playing_txt(format: str = Query(default=DEFAULT_TEXT, max_length=300)):
    """Now-playing as one text line. `?format=` is a template with
    {title} {artist} {album} {elapsed} {duration} placeholders — unknown
    fields and missing values render as ''. Text (not JSON) on purpose:
    OBS's classic Text source wants a plain line."""
    snap = _payload()

    def _fmt(ms):
        if ms is None:
            return ""
        s = int(ms) // 1000
        return f"{s // 60}:{s % 60:02d}"

    out = format
    for key in ("title", "artist", "album"):
        out = out.replace("{" + key + "}", snap.get(key) or "")
    out = out.replace("{elapsed}", _fmt(snap.get("elapsedMs")))
    out = out.replace("{duration}", _fmt(snap.get("durationMs")))
    # strip dangling separators when nothing is playing (" — " etc.)
    out = out.replace("— —", "—").strip().strip("—-").strip()
    return out + "\n"
