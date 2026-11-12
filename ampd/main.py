"""ampd — a personal, self-hosted Apple Music API driven through your own
logged-in web player session."""
import asyncio
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, FileResponse

from .config import config
from .browser import browser, BrowserError
from .errors import ApiError, install_error_handlers
from .models import Health
from .routes import (library, favorites, playback, passthrough, catalog,
                     personal, writes, sweeps, stream, audio, metrics, debug,
                     history, overlay)

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(name)s %(levelname)s %(message)s")

log = logging.getLogger("ampd")


@asynccontextmanager
async def lifespan(app):
    # audio pipeline starts eagerly, BEFORE the process is multithreaded:
    # spawning subprocesses from the running event loop wedges the loop
    # (fork-vs-GIL deadlock — found with py-spy the hard way)
    if config.audio_enabled and not config.mock_enabled:
        try:
            from .audio import broadcaster
            broadcaster.prestart()
        except Exception as e:
            log.error("audio pipeline failed to start: %s", e)
    # local store (v0.3 Memory): opens the db and arms the history writer —
    # one flat daemon thread that drains the stream-hook buffer. Never
    # started when AMPD_STORE is unset; everything history answers 501 then.
    if config.store_enabled:
        try:
            from .store import store, HistoryWriter, SnapshotScheduler
            from .browser import browser as _b
            from . import musickit as _mk
            store.start()
            _writer = HistoryWriter(store, _b, _mk)
            _writer.start()
            _snap = SnapshotScheduler(store, _b, _mk)
            _snap.start()
            import ampd.store as _store_mod
            _store_mod.history_writer = _writer
            _store_mod.snapshot_scheduler = _snap
        except Exception as e:
            log.error("store failed to start (continuing without it): %s", e)
    # scheduled exports (heavy walks — OFF unless AMPD_EXPORT_INTERVAL>0;
    # independent of the store: its outputs are files on the volume)
    if config.export_interval > 0:
        try:
            from .exporter import ExportScheduler
            from .browser import browser as _b
            from . import musickit as _mk
            from .store import store as _store
            _exp = ExportScheduler(_b, _mk, store=_store)
            _exp.start()
            import ampd.exporter as _exp_mod
            _exp_mod.export_scheduler = _exp
        except Exception as e:
            log.error("export scheduler failed to start: %s", e)
    # Discord Rich Presence (opt-in: AMPD_DISCORD=1) — daemon thread that
    # reads the stream's emitted state; a hiccup can never touch the server
    try:
        from . import discord
        discord.start()
    except Exception as e:
        log.error("discord bridge failed to start: %s", e)
    # Last.fm scrobbler (opt-in: AMPD_LASTFM=1) — needs the store (the
    # dedupe marker lives there); rides the same event buffer as the writer
    if config.lastfm_enabled:
        try:
            from .lastfm import Scrobbler, load_creds
            from .store import store
            creds = load_creds()
            if creds and creds.get("sk"):
                Scrobbler(store, creds).start()
            else:
                log.warning("lastfm: AMPD_LASTFM=1 but no session key — "
                            "run `python -m ampd.lastfm` first")
        except Exception as e:
            log.error("lastfm scrobbler failed to start: %s", e)
    yield
    try:
        from .store import store
        store.close()
    except Exception:
        pass


app = FastAPI(
    title="ampd",
    description="Unofficial personal Apple Music API — powered by your own "
                "logged-in web player session. Not affiliated with Apple.",
    version="0.5.1",
    lifespan=lifespan,
)


# the auth dialect is enforced by middleware, not a FastAPI dependency, so
# OpenAPI can't see it — document it explicitly. Generated clients (CI on
# release tags) read this and speak both flavors out of the box.
def _openapi_with_auth():
    if app.openapi_schema:
        return app.openapi_schema
    from fastapi.openapi.utils import get_openapi
    schema = get_openapi(title=app.title, version=app.version,
                         description=app.description, routes=app.routes)
    schema["components"]["securitySchemes"] = {
        "bearerAuth": {"type": "http", "scheme": "bearer",
                       "description": "Authorization: Bearer <AMPD_API_KEY>"},
        "apiKeyQuery": {"type": "apiKey", "in": "query", "name": "api_key",
                        "description": "?api_key=<AMPD_API_KEY> — the "
                                       "fallback EventSource needs (it "
                                       "cannot send headers)"},
    }
    schema["security"] = [{"bearerAuth": []}, {"apiKeyQuery": []}]
    app.openapi_schema = schema
    return schema


app.openapi = _openapi_with_auth


@app.middleware("http")
async def auth_guard(request: Request, call_next):
    path = request.url.path
    # the key guards the API SURFACE (/api/, /metrics) — the PWA shell and
    # the demo page load without it (#90): a locked-down server must still
    # serve the login page, and the shell itself carries no data. EventSource
    # can't send headers, so the key rides ?api_key= there; both dialects
    # are accepted everywhere.
    if config.api_key and (path.startswith("/api/") or path == "/metrics"):
        auth = request.headers.get("Authorization", "")
        key = request.query_params.get("api_key", "")
        if auth != f"Bearer {config.api_key}" and key != config.api_key:
            return JSONResponse(status_code=401, content={
                "error": {"code": "unauthorized",
                          "hint": "pass 'Authorization: Bearer <key>' "
                                  "(or ?api_key= for EventSource)"}})
    return await call_next(request)


install_error_handlers(app)


@app.get("/health", response_model=Health)
def health():
    if config.mock_enabled:
        return {"status": "ok", "browser": "mock (AMPD_MOCK=1)",
                "watchdog": None}
    wd = browser.health()
    try:
        browser.check()
        return {"status": "ok", "browser": "authorized", "watchdog": wd}
    except BrowserError as e:
        return JSONResponse(status_code=503, content={
            "status": "degraded", "detail": str(e), "watchdog": wd})


app.include_router(library.router, prefix="/api")
app.include_router(catalog.router, prefix="/api")
app.include_router(personal.router, prefix="/api")
app.include_router(favorites.router, prefix="/api")
app.include_router(playback.router, prefix="/api")
app.include_router(passthrough.router, prefix="/api")
app.include_router(writes.router, prefix="/api")
app.include_router(sweeps.router, prefix="/api")
app.include_router(stream.router, prefix="/api")
app.include_router(audio.router, prefix="/api")
app.include_router(metrics.router)
app.include_router(debug.router, prefix="/api")
app.include_router(history.router, prefix="/api")
app.include_router(overlay.router, prefix="/api")


@app.get("/demo", include_in_schema=False)
def demo():
    """Minimal live player UI — example of what the streaming API enables."""
    return FileResponse(os.path.join(os.path.dirname(__file__), "demo", "index.html"),
                        media_type="text/html")


# ---- PWA static serving (#84) — LAST, so every API route above wins ----
# web/ is built by `node web/build.mjs` (esbuild — the only npm dep) into
# ampd/web-dist; CI and the Docker build stage both run it (the runtime
# image has NO node). Missing dist => the API still boots fine; only the
# SPA 404s. The service worker is served from the root so its scope is "/".
_WEB_DIST = os.path.join(os.path.dirname(__file__), "web-dist")
if os.path.isdir(_WEB_DIST):
    from fastapi.staticfiles import StaticFiles
    app.mount("/", StaticFiles(directory=_WEB_DIST, html=True),
              name="pwa")
else:
    log.info("web-dist not built — the PWA is not served "
             "(run: node web/build.mjs)")
