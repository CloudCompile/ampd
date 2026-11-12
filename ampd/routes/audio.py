"""Audio stream routes — the actual sound, not just metadata."""
import asyncio

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from ..audio import broadcaster
from ..config import config

router = APIRouter(prefix="/audio", tags=["audio"])


def _mock_404():
    """Honest mock behavior (#80): there is no renderer producing sound,
    so there is no stream. 404 — never a fake audio feed."""
    if config.mock_enabled:
        raise HTTPException(404, "no audio in mock mode (AMPD_MOCK=1) — "
                                 "there is no renderer producing sound")


@router.get("/stream.mp3")
async def stream_mp3(request: Request):
    """Live mp3 of whatever the server's Apple Music session is playing.
    Point an <audio> element at it. ~1-2 s behind the reported playhead."""
    _mock_404()
    q = await asyncio.to_thread(broadcaster.subscribe)  # never block the loop

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
            broadcaster.unsubscribe(q)

    return StreamingResponse(gen(), media_type="audio/mpeg",
                             headers={"Cache-Control": "no-store",
                                      "X-Accel-Buffering": "no"})


@router.get("/status")
def status():
    _mock_404()
    return broadcaster.status()
