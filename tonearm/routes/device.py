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


@router.post("/tidbyt/report", response_model=DeviceAck)
def report_tidbyt(body: DeviceReport, request: Request):
    identity = getattr(request.state, "identity", None)
    report = body.model_dump()
    report["received_at"] = time.time()
    report["key_id"] = identity.describe() if identity else "keyless"
    with _lock:
        _last[body.device] = report
    return {"ok": True, "received_at": report["received_at"]}


@router.get("/tidbyt/status", response_model=dict[str, dict])
def tidbyt_status():
    with _lock:
        return {"devices": dict(_last)}
