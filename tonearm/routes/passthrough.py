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


# one registration per method: a multi-method api_route gets ONE
# unique_id shared by all five operations, and FastAPI's OpenAPI
# collision resolution is a warning + last-write — the schema's
# operationId flip-flopped between runs (hash order), which made the
# snapshot un-diffable (#128). Five registrations = five stable ids.
def _passthrough_route(method):
    return router.api_route(
        "/{path:path}", methods=[method], name=f"passthrough-{method.lower()}",
        generate_unique_id_function=lambda r, m=method: f"passthrough_{m.lower()}_amp_api")


@_passthrough_route("GET")
@_passthrough_route("POST")
@_passthrough_route("PUT")
@_passthrough_route("DELETE")
@_passthrough_route("PATCH")
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
