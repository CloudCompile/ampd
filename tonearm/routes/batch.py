"""The batch endpoint (#183): one round trip for N reads.

The client story this kills: the tunnel charges a round trip per call,
and one dashboard render (Ledger) was five of them. POST /api/batch
takes an array of {path, params} and answers with an array of
{status, body} envelopes.

Rules that keep it safe and boring:
* READS ONLY — every entry is served as a GET. There is no method
  field; mutations have no way in. This is v1 of the feature.
* paths must start with /api/ (the app's own surface — no proxying),
  /api/batch itself and the streaming surfaces are rejected (recursion,
  and SSE inside a JSON response is a category error).
* max 10 per batch — the point is collapsing round trips, not shipping
  a work queue. Params ride the read cache like any GET.
"""

from __future__ import annotations

import httpx as httpx2                  # the httpx fork; TestClient's dep
from fastapi import APIRouter, HTTPException, Request

from ..models import _PassThrough

router = APIRouter(tags=["batch"])

MAX_BATCH = 10
# streaming surfaces can't be answered inside a JSON envelope
DENIED = ("/api/batch", "/api/stream", "/api/audio/", "/metrics")


class BatchEntry(_PassThrough):
    """One inner result: {status, body} — body is whatever the inner
    route would have answered (error envelope on 4xx/5xx)."""
    status: int
    body: object = None


class BatchRequest(_PassThrough):
    requests: list[dict]


def _entries(raw: list[dict]) -> list[tuple[str, dict]]:
    if len(raw) > MAX_BATCH:
        raise HTTPException(400, f"max {MAX_BATCH} requests per batch — "
                                 f"the point is collapsing round trips, "
                                 f"not shipping a work queue")
    out = []
    for i, entry in enumerate(raw):
        if not isinstance(entry, dict):
            raise HTTPException(400, f"request[{i}] must be an object "
                                     f"with a 'path'")
        path = str(entry.get("path") or "")
        if not path.startswith("/api/"):
            raise HTTPException(400, f"request[{i}].path must start with "
                                     f"/api/ — batch only serves this "
                                     f"server's own reads")
        if path.startswith(DENIED):
            raise HTTPException(400, f"request[{i}].path: {path.split('?')[0]}"
                                     f" can't ride inside a batch envelope")
        params = entry.get("params") or {}
        if not isinstance(params, dict) or \
                not all(isinstance(v, (str, int, float, bool))
                        for v in params.values()):
            raise HTTPException(400, f"request[{i}].params must be a flat "
                                     f"string/value object")
        out.append((path, {k: str(v) for k, v in params.items()}))
    return out


@router.post("/batch", response_model=list[BatchEntry])
async def batch(batch: BatchRequest, request: Request):
    """N reads, one round trip. Every entry is answered as its own
    envelope: {status, body} (4xx/5xx per-entry — one bad request never
    sinks the batch)."""
    entries = _entries(batch.requests)

    # the inner calls run the full app (middleware included) in-process —
    # zero network. Auth rides the SAME key the batch itself presented:
    # a scoped key can't read more in a batch than it could alone.
    auth = request.headers.get("Authorization") or ""
    api_key = request.query_params.get("api_key") or ""
    transport = httpx2.ASGITransport(app=request.app)
    results: list[BatchEntry] = []
    async with httpx2.AsyncClient(transport=transport,
                                  base_url="http://inner") as client:
        for path, params in entries:
            if api_key:
                params = {**params, "api_key": api_key}
            try:
                r = await client.get(path, params=params, headers={
                    "Authorization": auth} if auth else {})
                try:
                    body = r.json()
                except Exception:
                    body = r.text
                results.append({"status": r.status_code, "body": body})
            except Exception as e:                 # one bad entry ≠ no batch
                results.append({"status": 502, "body": {
                    "error": {"code": "batch_entry_failed",
                              "hint": str(e)[:160]}}})
    return results
