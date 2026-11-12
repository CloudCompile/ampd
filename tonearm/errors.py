"""The one error shape: `{"error": {"code": "...", "hint": "..."}}`.

v0.4 contract: EVERY non-2xx response — any route, any failure class —
renders this envelope. Machine-actable `code`s (stable, documented in the
README), human `hint`s. Built as exception HANDLERS, not per-route edits:
routes keep raising HTTPException exactly as before, and the envelope is
guaranteed centrally (one place to audit — an error path that can leak an
unwrapped shape is how clients end up string-matching).

Raise `ApiError` where the status alone can't pick the right code (e.g.
writes_disabled vs store_disabled are both 501s with different fixes).
"""
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

# status -> default code when nothing more specific was raised
STATUS_CODES = {
    400: "bad_request",
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    405: "method_not_allowed",
    429: "rate_limited",
    500: "internal_error",
    501: "disabled",
    502: "renderer_unavailable",
    503: "degraded",
}

# default human hints when the raised exception has no detail
STATUS_HINTS = {
    400: "check the parameters — the hint names the problem when known",
    401: "pass 'Authorization: Bearer <key>' (or ?api_key= for EventSource)",
    404: "no such resource or route",
    429: "slow down — retry after the delay stated in Retry-After",
    500: "something broke server-side — check the server log",
    502: "the renderer (your Chrome tab) is busy or stalled — it usually "
         "recovers on its own within ~60s; retry shortly",
    501: "this surface is disabled — the detail names the env flag to set",
    503: "the renderer is degraded — /health carries the watchdog detail",
}


class ApiError(Exception):
    """Explicit envelope error — use when the status alone can't pick
    the code (501s: writes_disabled vs store_disabled; 502s: busy vs
    unauthorized renderer)."""

    def __init__(self, status: int, code: str, hint: str = ""):
        self.status = status
        self.code = code
        self.hint = hint or STATUS_HINTS.get(status, "")
        super().__init__(f"{code}: {self.hint}")


def envelope_content(status, code=None, detail=""):
    """Pure shape builder: the ONLY place the error shape is defined.
    `(status, {"error": {"code", "hint"}})` — testable without HTTP."""
    return status, {"error": {
        "code": code or STATUS_CODES.get(status, "error"),
        "hint": detail if isinstance(detail, str) and detail
                else STATUS_HINTS.get(status, ""),
    }}


def wrap_http_exception(exc: StarletteHTTPException):
    """Plain HTTPException (routing 404s, per-route raises) -> envelope.
    The exception's detail, when it has one, IS the human hint."""
    return envelope_content(exc.status_code, detail=exc.detail)


def wrap_validation_error(exc: RequestValidationError):
    """Request validation (422s) -> 400 bad_request with the first problem
    as the hint — a caller wants to know what to fix, all of it."""
    errs = exc.errors()
    first = ""
    if errs:
        e0 = errs[0]
        first = f"{'.'.join(str(x) for x in e0.get('loc', [])[1:])}: " \
                f"{e0.get('msg', '')}"
    return envelope_content(400, "bad_request", first)


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def _api_error(request: Request, exc: ApiError):
        status, content = envelope_content(exc.status, exc.code, exc.hint)
        return JSONResponse(status_code=status, content=content)

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(request: Request, exc: StarletteHTTPException):
        status, content = wrap_http_exception(exc)
        return JSONResponse(status_code=status, content=content)

    @app.exception_handler(RequestValidationError)
    async def _validation_error(request: Request, exc: RequestValidationError):
        status, content = wrap_validation_error(exc)
        return JSONResponse(status_code=status, content=content)
