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
from .routes import (library, favorites, playback, passthrough, catalog,
                     personal, writes, sweeps, stream, audio)

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(name)s %(levelname)s %(message)s")

log = logging.getLogger("ampd")


@asynccontextmanager
async def lifespan(app):
    # audio pipeline starts eagerly, BEFORE the process is multithreaded:
    # spawning subprocesses from the running event loop wedges the loop
    # (fork-vs-GIL deadlock — found with py-spy the hard way)
    if config.audio_enabled:
        try:
            from .audio import broadcaster
            broadcaster.start()
        except Exception as e:
            log.error("audio pipeline failed to start: %s", e)
    yield


app = FastAPI(
    title="ampd",
    description="Unofficial personal Apple Music API — powered by your own "
                "logged-in web player session. Not affiliated with Apple.",
    version="0.2.0",
    lifespan=lifespan,
)


@app.middleware("http")
async def auth_guard(request: Request, call_next):
    if config.api_key and request.url.path not in ("/health", "/demo"):
        # EventSource can't send headers, so the demo page passes the key
        # as a query param instead
        auth = request.headers.get("Authorization", "")
        key = request.query_params.get("api_key", "")
        if auth != f"Bearer {config.api_key}" and key != config.api_key:
            return JSONResponse(status_code=401, content={"detail": "bad api key"})
    return await call_next(request)


@app.get("/health")
def health():
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


@app.get("/demo", include_in_schema=False)
def demo():
    """Minimal live player UI — example of what the streaming API enables."""
    return FileResponse(os.path.join(os.path.dirname(__file__), "demo", "index.html"),
                        media_type="text/html")
