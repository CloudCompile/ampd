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
import time

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from .. import musickit as mk
from ..browser import BrowserError

router = APIRouter(tags=["stream"])


async def _events(request: Request):
    try:
        mk.install_stream_hook()
        snap = await asyncio.to_thread(mk.snapshot)
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
                yield f"event: update\ndata: {json.dumps(e)}\n\n"
            if time.time() - last_send > 15:
                yield ": hb\n\n"
                last_send = time.time()
            await asyncio.sleep(1.0)
    except (BrowserError, GeneratorExit, asyncio.CancelledError):
        return


@router.get("/stream")
def stream(request: Request):
    return StreamingResponse(_events(request), media_type="text/event-stream",
                             headers={"Cache-Control": "no-store",
                                      "X-Accel-Buffering": "no"})
