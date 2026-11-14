"""Small authenticated device telemetry inbox for remote Tidbyt development.

Device initiated only: the ESP32 POSTs a compact heartbeat over its existing
outbound HTTP relay. We retain the latest report per device in process memory;
no log credentials, secrets, or arbitrary request headers are stored.
"""
from __future__ import annotations

import threading
import time

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

router = APIRouter(prefix="/device", tags=["device"])
_lock = threading.Lock()
_last: dict[str, dict] = {}
_opencode: dict[str, dict] = {}


class DeviceReport(BaseModel):
    device: str = Field(default="tidbyt", max_length=40)
    version: str | None = Field(default=None, max_length=48)
    ip: str | None = Field(default=None, max_length=48)
    wifi_rssi: int | None = None
    free_heap: int | None = None
    uptime_s: int | None = None
    reset_reason: str | None = Field(default=None, max_length=64)
    ota_status: str | None = Field(default=None, max_length=32)
    state: str | None = Field(default=None, max_length=64)


class DeviceAck(BaseModel):
    ok: bool
    received_at: float


class DeviceStatusSnapshot(BaseModel):
    devices: dict[str, dict]
    opencode: dict[str, dict]


class OpenCodeReport(BaseModel):
    session_id: str = Field(max_length=80)
    state: str = Field(default="busy", max_length=24)
    project: str = Field(default="", max_length=18)
    activity: str = Field(default="working", max_length=20)


@router.post("/tidbyt/report", response_model=DeviceAck)
def report_tidbyt(body: DeviceReport, request: Request):
    identity = getattr(request.state, "identity", None)
    report = body.model_dump()
    report["received_at"] = time.time()
    report["key_id"] = identity.describe() if identity else "keyless"
    with _lock:
        _last[body.device] = report
    return {"ok": True, "received_at": report["received_at"]}


@router.get("/tidbyt/status", response_model=DeviceStatusSnapshot)
def tidbyt_status():
    with _lock:
        return {"devices": dict(_last), "opencode": dict(_opencode)}


@router.post("/tidbyt/opencode")
def report_opencode(body: OpenCodeReport, request: Request):
    """Accept only a short, allowlisted session summary; never accept
    prompts, code, tool arguments, or arbitrary event payloads."""
    identity = getattr(request.state, "identity", None)
    report = {
        "session_id": body.session_id,
        "state": body.state if body.state in {"busy", "idle", "error"} else "busy",
        "project": body.project[:18],
        "activity": body.activity[:20],
        "received_at": time.time(),
        "key_id": identity.describe() if identity else "keyless",
    }
    with _lock:
        _opencode[body.session_id] = report
        # Bound retained sessions; this is an activity display, not an archive.
        if len(_opencode) > 12:
            oldest = min(_opencode, key=lambda k: _opencode[k]["received_at"])
            del _opencode[oldest]
    return {"ok": True, "received_at": report["received_at"]}
