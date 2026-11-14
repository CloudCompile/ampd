"""Browser serial bridge.

The page at /serial (served to the user's Chrome, which holds the Tidbyt's
USB serial port via Web Serial) mirrors every byte the device emits to the
WebSocket below, and polls an ops queue that agents drive:

  POST /api/device/serial/ops   agent queues ops: {"op": "flash", "url": ...}
                                 {"op": "chip_id"}, {"op": "reset"}   (write key)
  GET  /api/device/serial/ops   page pops the queue                  (device key)
  POST /api/device/serial/results   page reports op outcomes + chip info
  GET  /api/device/serial/results   agent reads outcomes
  GET  /api/device/serial/console   agent reads the live serial stream
  GET  /serial                      the page itself (main.py serves it)
  WS   /serial-ws                   the raw byte bridge (uplink: device logs;
                                    downlink: bytes to write to the device)

Flashing happens IN THE BROWSER via esptool-js (same engine as
web.esphome.io), so the VPS never touches USB — the user just keeps the
page open with the device plugged in.
"""
import json
import os
import time
from collections import deque
from urllib.parse import urlparse

from fastapi import APIRouter, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse

router = APIRouter()

CAPTURE = "/tmp/serial-capture.log"
ALLOWED_HOSTS = {"remote.tail4c21bf.ts.net:10000", "remote.tail4c21bf.ts.net",
                 "20.221.210.24"}

_ops: list = []
_results: deque = deque(maxlen=200)
_console: deque = deque(maxlen=800)


@router.post("/api/device/serial/ops")
async def push_op(request: Request):
    identity = getattr(request.state, "identity", None)
    if identity is None or not identity.can_write:
        raise HTTPException(403, "write key required")
    body = await request.json()
    op = body.get("op")
    if not op:
        raise HTTPException(400, "op required")
    _ops.append({**body, "queued_at": time.time()})
    return {"ok": True, "pending": len(_ops)}


@router.get("/api/device/serial/ops")
async def get_ops(pop: int = 1):
    out = list(_ops)
    if pop:
        _ops.clear()
    return {"ops": out}


@router.post("/api/device/serial/results")
async def post_result(request: Request, body: dict):
    body["received_at"] = time.time()
    _results.append(body)
    return {"ok": True, "stored": len(_results)}


@router.get("/api/device/serial/results")
async def get_results(n: int = 20):
    return {"results": list(_results)[-n:]}


@router.get("/api/device/serial/console")
async def console(n: int = 150):
    return {"log": list(_console)[-n:]}


@router.get("/api/device/serial/file")
async def proxy_file(url: str):
    """Stream a firmware file to the page. The page origin (:8443) differs
    from the funnel file host (:10000), and the file server sends no CORS
    headers, so the page fetches through here. Host allowlisted."""
    p = urlparse(url)
    if p.scheme not in ("http", "https") or p.netloc not in ALLOWED_HOSTS:
        raise HTTPException(400, "host not allowed")
    import urllib.request
    up = urllib.request.urlopen(url, timeout=60)

    def gen():
        try:
            while True:
                chunk = up.read(65536)
                if not chunk:
                    break
                yield chunk
        finally:
            up.close()

    return StreamingResponse(gen(), media_type="application/octet-stream",
                             headers={"Access-Control-Allow-Origin": "*"})


@router.websocket("/serial-ws")
async def serial_ws(ws: WebSocket):
    await ws.accept()
    try:
        while True:
            msg = await ws.receive()
            if msg.get("type") == "websocket.disconnect":
                break
            data = msg.get("bytes")
            if data:
                text = data.decode("utf-8", "replace")
                _console.append(text)
                try:
                    with open(CAPTURE, "ab") as f:
                        f.write(data)
                except OSError:
                    pass
                continue
            text = msg.get("text")
            if text:
                # control/status messages from the page ("connected", "closed")
                _console.append(f"[page] {text}")
    except WebSocketDisconnect:
        pass
    finally:
        try:
            await ws.close()
        except Exception:
            pass
