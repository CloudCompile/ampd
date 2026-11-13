"""Streaming API — server-sent events of player state.

GET /api/stream  (text/event-stream)
  -> `event: snapshot` with the full state on connect
  -> `event: update`   with every player change (play/pause, track change,
     progress ~1/s, queue changes, shuffle/repeat)
  -> `: hb` comment every ~15s so proxies keep the connection warm

Built so custom UIs can render live without polling: point an EventSource
at it and re-render on every message. See /demo for a working example.
"""
import asyncio
import json
import threading
import time

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, StreamingResponse

from .. import musickit as mk
from .. import keys as keys_mod
from ..browser import BrowserError
from ..metrics import METRICS

router = APIRouter(tags=["stream"])

_listeners = 0
_listener_lock = threading.Lock()

# the last state this SSE generator emitted (snapshot or any update) — the
# OBS overlay route serves from here, so streamers trigger ZERO extra
# Chrome evals: the overlay piggybacks on data the stream already fetched
_last = {"isPlaying": False, "state": 0, "title": None, "artist": None,
         "album": None, "id": None, "durationMs": None, "elapsedMs": None,
         "progress": None, "volume": None, "shuffle": None, "repeat": None,
         "artworkUrl": None}
_last_lock = threading.Lock()


def last_snapshot():
    """Copy of the most recent player state the SSE stream emitted."""
    with _last_lock:
        return dict(_last)


def _remember(d):
    with _last_lock:
        _last.update(d)
    # feed the join-alignment state (#95): the audio routes stamp join
    # headers from this — no Chrome evals from the audio side, ever
    try:
        from ..audio import note_playhead
        note_playhead(d.get("elapsedMs"), d.get("isPlaying"))
    except Exception:
        pass                                          # audio is optional


def _listener_delta(d):
    global _listeners
    with _listener_lock:
        _listeners = max(0, _listeners + d)
        METRICS.gauge("tonearm_stream_listeners", _listeners,
                      help_text="Active SSE /api/stream connections")
        return _listeners


async def _events(request: Request):
    _listener_delta(1)
    try:
        mk.install_stream_hook()
        snap = await asyncio.to_thread(mk.snapshot)
        _remember(snap)
        yield f"event: snapshot\ndata: {json.dumps(snap)}\n\n"
        after = 0
        last_send = time.time()
        fails = 0
        while True:
            if await request.is_disconnected():
                return
            try:
                entries = await asyncio.to_thread(mk.drain_stream, after)
                fails = 0
            except (BrowserError, Exception) as e:
                # transient chrome stall — keep the connection, back off
                fails += 1
                if fails > 30:
                    return
                last_send = time.time()
                await asyncio.sleep(min(1.0 * fails, 5.0))
                continue
            for e in entries:
                after = e["seq"]
                last_send = time.time()
                _remember(e)
                yield f"event: update\ndata: {json.dumps(e)}\n\n"
            if time.time() - last_send > 15:
                yield ": hb\n\n"
                last_send = time.time()
            await asyncio.sleep(1.0)
    except (BrowserError, GeneratorExit, asyncio.CancelledError):
        return
    finally:
        _listener_delta(-1)
        if identity is not None:
            keys_mod.sse_cap.leave(identity)


@router.get("/stream")
def stream(request: Request):
    # per-key SSE connection cap (#118): the master is unlimited; a scoped
    # key gets a small concurrent-stream allowance (a tab family, not a
    # fleet of tabs). Rejected here, before the generator starts.
    identity = getattr(request.state, "identity", None)
    if identity is not None and not keys_mod.sse_cap.enter(identity):
        return JSONResponse(
            status_code=429,
            content={"error": {"code": "rate_limited",
                               "hint": f"key {identity.describe()} hit its "
                                       f"concurrent-stream cap"}})
    return StreamingResponse(_events(request), media_type="text/event-stream",
                             headers={"Cache-Control": "no-store",
                                      "X-Accel-Buffering": "no"})
