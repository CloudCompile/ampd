"""Wildcard pass-through: any amp-api path with your tokens injected.

This is the escape hatch — everything Apple's web player can do, this endpoint
can forward. Examples:

  curl 'http://127.0.0.1:8188/amp-api/v1/me/library/songs?limit=5'
  curl -X POST 'http://127.0.0.1:8188/amp-api/v1/me/favorites?ids[songs]=1234'
"""
import json

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from .. import musickit as mk
from ..browser import BrowserError

router = APIRouter(prefix="/amp-api", tags=["amp-api pass-through"])


@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def passthrough(path: str, request: Request):
    body = None
    if request.method in ("POST", "PUT", "PATCH", "DELETE"):
        raw = await request.body()
        if raw:
            try:
                body = json.loads(raw)
            except json.JSONDecodeError:
                raise HTTPException(400, "body must be JSON")
    # rebuild the full query string exactly as the caller sent it
    qs = request.url.query
    full_path = "/" + path.lstrip("/")
    if qs:
        full_path += "?" + qs
    try:
        res = mk.raw_api(full_path, method=request.method, body=body)
    except BrowserError as e:
        raise HTTPException(502, str(e))
    try:
        payload = json.loads(res["body"]) if res["body"] else None
    except json.JSONDecodeError:
        payload = res["body"]
    return JSONResponse(status_code=res["status"], content=payload)
