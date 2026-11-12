"""GET /metrics — Prometheus exposition. Reads only from state the live
layers already maintain (never evals the renderer at scrape time)."""
from fastapi import APIRouter, Response

from ..audio import broadcaster
from ..browser import browser
from ..metrics import METRICS

router = APIRouter(tags=["metrics"])


@router.get("/metrics")
def metrics():
    """Prometheus text format. Carries no user data, but sits behind
    TONEARM_API_KEY when one is set (scrape config: `authorization` block with
    `Authorization: Bearer <key>`)."""
    wd = browser.health()
    METRICS.gauge("tonearm_renderer_consecutive_failures",
                  wd.get("consecutive_failures") or 0,
                  help_text="Watchdog: consecutive failed renderer pings "
                            "(0 = healthy; recovery resets this)")
    METRICS.gauge("tonearm_renderer_last_ping_ok",
                  1 if wd.get("last_ok") else 0,
                  help_text="Watchdog: 1 when the last ping succeeded")
    METRICS.gauge("tonearm_renderer_recycles",
                  wd.get("recycles") or 0,
                  help_text="Watchdog: dead-tab recycles since start "
                            "(monotonic gauge — the source of truth lives in "
                            "the watchdog snapshot)")
    aud = broadcaster.status()
    METRICS.gauge("tonearm_audio_listeners", aud.get("listeners") or 0,
                  help_text="Active /api/audio/stream.mp3 listeners")
    METRICS.gauge("tonearm_audio_pipeline_running", 1 if aud.get("running") else 0,
                  help_text="Audio capture pipeline up (parec|ffmpeg)")
    return Response(content=METRICS.render(), media_type="text/plain; version=0.0.4; charset=utf-8")
