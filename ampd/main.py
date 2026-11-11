"""ampd — a personal, self-hosted Apple Music API driven through your own
logged-in web player session."""
import logging

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse

from .config import config
from .browser import browser, BrowserError
from .routes import library, favorites, playback, passthrough

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(name)s %(levelname)s %(message)s")

app = FastAPI(
    title="ampd",
    description="Unofficial personal Apple Music API — powered by your own "
                "logged-in web player session. Not affiliated with Apple.",
    version="0.1.0",
)


@app.middleware("http")
async def auth_guard(request: Request, call_next):
    if config.api_key and request.url.path not in ("/health",):
        auth = request.headers.get("Authorization", "")
        if auth != f"Bearer {config.api_key}":
            return JSONResponse(status_code=401, content={"detail": "bad api key"})
    return await call_next(request)


@app.get("/health")
def health():
    try:
        browser.check()
        return {"status": "ok", "browser": "authorized"}
    except BrowserError as e:
        return JSONResponse(status_code=503, content={"status": "degraded", "detail": str(e)})


app.include_router(library.router, prefix="/api")
app.include_router(favorites.router, prefix="/api")
app.include_router(playback.router, prefix="/api")
app.include_router(passthrough.router, prefix="/api")
