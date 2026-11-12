"""Audio stream routes — the actual sound, not just metadata.

Formats (#92): /stream.mp3 (the original URL), /stream.ogg (vorbis),
/stream.opus. Each active format gets its own encoder reading the same
private sink — one subprocess per FORMAT, never per listener.
Loudness normalization (#93): ?loudnorm=1 (or AMPD_AUDIO_LOUDNORM=1).
Join alignment (#95): X-AMPD-Join-* headers describe the playhead at join;
the feed starts with a pre-encoded silence pad so clients have a
deterministic alignment point (the pipe is live — never seekable).
"""
import asyncio

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from ..audio import FORMATS, AudioError, broadcaster
from ..config import config

router = APIRouter(prefix="/audio", tags=["audio"])


def _mock_404():
    """Honest mock behavior (#80): there is no renderer producing sound,
    so there is no stream. 404 — never a fake audio feed."""
    if config.mock_enabled:
        raise HTTPException(404, "no audio in mock mode (AMPD_MOCK=1) — "
                                 "there is no renderer producing sound")


async def _stream(fmt, bitrate, loudnorm, request):
    _mock_404()
    spec = FORMATS[fmt]

    def _sub():                                      # never block the loop
        try:
            return broadcaster.subscribe(fmt, bitrate, loudnorm), None
        except AudioError as e:
            return None, str(e)

    (q, meta), err = await asyncio.to_thread(_sub)
    if err:
        raise HTTPException(400, err)

    async def gen():
        try:
            while True:
                if await request.is_disconnected():
                    return
                try:
                    chunk = await asyncio.to_thread(q.get, timeout=1.0)
                    yield chunk
                except Exception:
                    continue                        # queue timeout — keep looping
        finally:
            await asyncio.to_thread(broadcaster.unsubscribe, q)

    # X-AMPD-Join-* (#95): pad_ms of pre-encoded silence comes FIRST; the
    # playhead claim is stamped with its staleness — a stale claim is said
    # loudly, never silently pretended
    headers = {"Cache-Control": "no-store", "X-Accel-Buffering": "no",
               "X-AMPD-Join-Pad-Ms": str(meta["pad_ms"]),
               "X-AMPD-Join-Playhead-Ms": "" if meta["playhead_ms"] is None
               else str(int(meta["playhead_ms"])),
               "X-AMPD-Join-Stale": "1" if meta["stale"] else "0",
               "X-AMPD-Audio-Format": fmt}
    return StreamingResponse(gen(), media_type=spec["type"], headers=headers)


@router.get("/stream.mp3")
async def stream_mp3(request: Request, bitrate: str = None,
                     loudnorm: int = None):
    """Live mp3 of whatever the server's Apple Music session is playing.
    Point an <audio> element at it. ~1-2 s behind the reported playhead —
    X-AMPD-Join-* headers describe the alignment at subscribe time."""
    _mock_404()
    ln = None if loudnorm is None else bool(loudnorm)
    return await _stream("mp3", bitrate, ln, request)


@router.get("/stream.ogg")
async def stream_ogg(request: Request, bitrate: str = None,
                     loudnorm: int = None):
    """Live Ogg Vorbis of the session's audio (same capture as mp3)."""
    _mock_404()
    ln = None if loudnorm is None else bool(loudnorm)
    return await _stream("ogg", bitrate, ln, request)


@router.get("/stream.opus")
async def stream_opus(request: Request, bitrate: str = None,
                      loudnorm: int = None):
    """Live Opus (in Ogg) of the session's audio — smallest bandwidth."""
    _mock_404()
    ln = None if loudnorm is None else bool(loudnorm)
    return await _stream("opus", bitrate, ln, request)


@router.get("/status")
def status():
    _mock_404()
    return broadcaster.status()
