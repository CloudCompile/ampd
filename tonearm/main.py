"""tonearm — a personal, self-hosted Apple Music API driven through your own
logged-in web player session."""
import asyncio
import logging
import os
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, FileResponse

from .config import config
from .browser import browser, BrowserError
from .errors import ApiError, install_error_handlers
from .metrics import METRICS
from .models import Health
from . import __version__
from . import keys as keys_mod
from .routes import (library, favorites, playback, passthrough, catalog,
                     personal, writes, sweeps, stream, audio, metrics, debug,
                     history, overlay, webhooks as webhooks_routes,
                     smartlists as smartlists_routes,
                     watcher as watcher_routes,
                     audit as audit_routes)

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(name)s %(levelname)s %(message)s")

log = logging.getLogger("tonearm")


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
    # started when TONEARM_STORE is unset; everything history answers 501 then.
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
            import tonearm.store as _store_mod
            _store_mod.history_writer = _writer
            _store_mod.snapshot_scheduler = _snap
        except Exception as e:
            log.error("store failed to start (continuing without it): %s", e)
    # scheduled exports (heavy walks — OFF unless TONEARM_EXPORT_INTERVAL>0;
    # independent of the store: its outputs are files on the volume)
    if config.export_interval > 0:
        try:
            from .exporter import ExportScheduler
            from .browser import browser as _b
            from . import musickit as _mk
            from .store import store as _store
            _exp = ExportScheduler(_b, _mk, store=_store)
            _exp.start()
            import tonearm.exporter as _exp_mod
            _exp_mod.export_scheduler = _exp
        except Exception as e:
            log.error("export scheduler failed to start: %s", e)
    # Discord Rich Presence (opt-in: TONEARM_DISCORD=1) — daemon thread that
    # reads the stream's emitted state; a hiccup can never touch the server
    try:
        from . import discord
        discord.start()
    except Exception as e:
        log.error("discord bridge failed to start: %s", e)
    # Last.fm scrobbler (opt-in: TONEARM_LASTFM=1) — needs the store (the
    # dedupe marker lives there); rides the same event buffer as the writer
    if config.lastfm_enabled:
        try:
            from .lastfm import Scrobbler, load_creds
            from .store import store
            creds = load_creds()
            if creds and creds.get("sk"):
                Scrobbler(store, creds).start()
            else:
                log.warning("lastfm: TONEARM_LASTFM=1 but no session key — "
                            "run `python -m tonearm.lastfm` first")
        except Exception as e:
            log.error("lastfm scrobbler failed to start: %s", e)
    # Outbound webhooks (opt-in: TONEARM_WEBHOOKS=1) — the delivery worker
    # and the stream watcher. Producers call webhooks.emit(); when off it is
    # a no-op, so every call site stays unconditional.
    try:
        from . import webhooks
        webhooks.start()
    except Exception as e:
        log.error("webhook engine failed to start: %s", e)
    # Scheduled sweep digests (opt-in: TONEARM_DIGEST_INTERVAL>0, needs
    # webhooks). A dry-run walk on a slow cadence; emits `sweep.digest`.
    if config.digest_interval > 0 and config.webhooks_enabled:
        try:
            from .digest import DigestScheduler
            from .browser import browser as _b
            _dig = DigestScheduler(_b)
            _dig.start()
            import tonearm.digest as _digest_mod
            _digest_mod.scheduler = _dig
        except Exception as e:
            log.error("digest scheduler failed to start: %s", e)
    # New-release watcher (opt-in: TONEARM_WATCHER=1, #42). It needs
    # somewhere to notify (webhooks) or somewhere to put new music
    # (auto-add playlist + writes) — otherwise a pass is wasted evals.
    if config.watcher_enabled:
        if config.webhooks_enabled or (config.watcher_auto_playlist
                                       and config.enable_writes):
            try:
                from .store import store as _store
                from .watcher import ReleaseWatcher
                from .browser import browser as _b
                from . import musickit as _mk
                _watch = ReleaseWatcher(_store, _b, _mk)
                _watch.start()
                import tonearm.watcher as _watcher_mod
                _watcher_mod.watcher = _watch
            except Exception as e:
                log.error("release watcher failed to start: %s", e)
        else:
            log.warning("watcher: TONEARM_WATCHER=1 but nothing to do — "
                        "set TONEARM_WEBHOOKS=1 (notify) or "
                        "TONEARM_WATCHER_PLAYLIST + TONEARM_ENABLE_WRITES "
                        "(auto-add)")
    # Smart-playlist engine (opt-in: TONEARM_SMARTLIST_INTERVAL>0; the
    # scheduler re-evaluates + materializes; CRUD works without it).
    if config.smartlist_interval > 0:
        try:
            from .store import store as _store
            from .smartlists import SmartlistScheduler
            from .browser import browser as _b
            _smart = SmartlistScheduler(_store, _b)
            _smart.start()
            import tonearm.smartlists as _smart_mod
            _smart_mod.scheduler = _smart
        except Exception as e:
            log.error("smartlist scheduler failed to start: %s", e)
    yield
    try:
        from . import digest as _digest_mod
        if getattr(_digest_mod, "scheduler", None) is not None:
            _digest_mod.scheduler.stop()
    except Exception:
        pass
    try:
        from . import webhooks
        webhooks.stop()
    except Exception:
        pass
    try:
        from .audio import broadcaster
        broadcaster.stop()          # kill capture subprocesses (#177)
    except Exception:
        pass
    try:
        from . import watcher as _watcher_mod
        if getattr(_watcher_mod, "watcher", None) is not None:
            _watcher_mod.watcher.stop()
    except Exception:
        pass
    try:
        from . import smartlists as _smart_mod
        if getattr(_smart_mod, "scheduler", None) is not None:
            _smart_mod.scheduler.stop()
    except Exception:
        pass
    try:
        from .store import store
        store.close()
    except Exception:
        pass


app = FastAPI(
    title="tonearm",
    description="Unofficial personal Apple Music API — powered by your own "
                "logged-in web player session. Not affiliated with Apple.",
    version=__version__,
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
                       "description": "Authorization: Bearer <TONEARM_API_KEY>"},
        "apiKeyQuery": {"type": "apiKey", "in": "query", "name": "api_key",
                        "description": "?api_key=<TONEARM_API_KEY> — the "
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
    # the key guards the API SURFACE (/api/, /metrics) — the PWA shell,
    # /demo and the companion pages load without it (#90): a locked-down
    # server must still serve its own UI (it carries no data). EventSource
    # can't send headers, so the key rides ?api_key= there; both dialects
    # are accepted everywhere.
    if not (path.startswith("/api/") or path == "/metrics"):
        return await call_next(request)
    # v0.7 multi-key: no master key AND no keys file = a keyless server,
    # exactly the old behavior. Anything configured resolves to an identity.
    if not config.api_key and not keys_mod.registry.has_keys():
        return await call_next(request)
    presented = request.headers.get("Authorization", "")
    if presented.startswith("Bearer "):
        presented = presented[7:]
    else:
        presented = request.query_params.get("api_key", "")
    identity = keys_mod.registry.resolve(presented)
    if identity is None:
        return JSONResponse(status_code=401, content={
            "error": {"code": "unauthorized",
                      "hint": "pass 'Authorization: Bearer <key>' "
                              "(or ?api_key= for EventSource)"}})
    # per-key rate ceiling (#116) — the master is never limited
    ok, retry = keys_mod.limiter.check(identity)
    if not ok:
        return JSONResponse(
            status_code=429, headers={"Retry-After": str(retry)},
            content={"error": {"code": "rate_limited",
                               "hint": f"key {identity.describe()} hit its "
                                       f"ceiling — retry after {retry}s"}})
    # scopes (#115): non-GET requires write — playback control included
    # (a friend's UI watches; yours drives)
    if request.method not in ("GET", "HEAD", "OPTIONS") \
            and not identity.can_write:
        return JSONResponse(status_code=403, content={
            "error": {"code": "insufficient_scope",
                      "hint": f"key {identity.describe()} is read-only — "
                              f"mutations need a write key"}})
    request.state.identity = identity
    response = await call_next(request)
    # per-key metrics (#119): keyed requests by key id + outcome class
    METRICS.inc("tonearm_api_requests_total",
                {"key": identity.describe(),
                 "code": f"{response.status_code // 100}xx"},
                help_text="API requests by key and status class")
    # the audit trail (#47): every authenticated MUTATION — who did what
    if request.method not in ("GET", "HEAD", "OPTIONS"):
        try:
            from . import audit
            audit.record(identity, request.method, path,
                         response.status_code)
        except Exception:                 # the audit never breaks the request
            pass
    return response


install_error_handlers(app)


@app.get("/health", response_model=Health)
def health():
    if config.mock_enabled:
        return {"status": "ok", "browser": "mock (TONEARM_MOCK=1)",
                "watchdog": None,
                "session": {"state": "mock", "since": time.time()}}
    wd = browser.health()
    try:
        browser.check()
        return {"status": "ok", "browser": "authorized", "watchdog": wd,
                "session": dict(mk.session_state)}
    except BrowserError as e:
        return JSONResponse(status_code=503, content={
            "status": "degraded", "detail": str(e), "watchdog": wd,
            "session": dict(mk.session_state)})


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
app.include_router(webhooks_routes.router, prefix="/api")
app.include_router(smartlists_routes.router, prefix="/api")
app.include_router(watcher_routes.router, prefix="/api")
app.include_router(audit_routes.router, prefix="/api")


@app.get("/demo", include_in_schema=False)
def demo():
    """Minimal live player UI — example of what the streaming API enables."""
    return FileResponse(os.path.join(os.path.dirname(__file__), "demo", "index.html"),
                        media_type="text/html")


# ---- companion pages (v0.6.2) — /ledger /radar /bench, served like /demo.
# Keyless shell, the PWA's auth dialect: the page loads without the key and
# the fetches carry it (Bearer from localStorage; a 401 prompts once).

_SITES = os.path.join(os.path.dirname(__file__), "sites")


@app.get("/ledger", include_in_schema=False)
def ledger_page():
    return FileResponse(os.path.join(_SITES, "ledger.html"),
                        media_type="text/html")


@app.get("/radar", include_in_schema=False)
def radar_page():
    return FileResponse(os.path.join(_SITES, "radar.html"),
                        media_type="text/html")


@app.get("/bench", include_in_schema=False)
def bench_page():
    return FileResponse(os.path.join(_SITES, "bench.html"),
                        media_type="text/html")


@app.get("/sites/{filename}", include_in_schema=False)
def site_asset(filename: str):
    """Static assets for the companion pages (js/css). Path-traversal safe:
    a flat allowlist check, no subdirectories, no dots."""
    if ("/" in filename or ".." in filename or filename.startswith(".")):
        raise HTTPException(404)
    path = os.path.join(_SITES, filename)
    if not os.path.isfile(path):
        raise HTTPException(404)
    media = {"js": "text/javascript", "css": "text/css"}.get(
        filename.rsplit(".", 1)[-1], "application/octet-stream")
    return FileResponse(path, media_type=media)


# ---- PWA static serving (#84) — LAST, so every API route above wins ----
# web/ is built by `node web/build.mjs` (esbuild — the only npm dep) into
# tonearm/web-dist; CI and the Docker build stage both run it (the runtime
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
