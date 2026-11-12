"""GET /api/debug — an operator's window into the CDP layer.

Rule (learned via /health hanging once): a debug surface must NEVER eval the
renderer it is diagnosing. Everything here reads state already held in
memory or the socket-free Chrome HTTP API:
  * last-N CDP calls with durations (ring buffer in browser._raw_call)
  * current music-tab URL (chrome /json/list — HTTP, not an eval)
  * renderer health snapshot (the watchdog's own dict)
  * webhook delivery status (v0.6: per-hook last attempt, parked state —
    memory-only, same eval-free discipline)
Gated behind TONEARM_API_KEY when set (it sits under /api like everything else).
"""
from fastapi import APIRouter

from ..browser import browser
from ..config import config
from ..models import DebugInfo

router = APIRouter(prefix="/debug", tags=["debug"])


def _webhook_status():
    """Delivery state per hook — last attempt (ts, status, latency) and the
    parked flag (#105). Reads only from the in-memory registry/worker ring:
    no evals, no HTTP."""
    if not config.webhooks_enabled:
        return None
    try:
        from .. import webhooks
        snap = webhooks.snapshot()
        return {"hooks": snap["hooks"], "pending": snap["pending"],
                "recent": snap["recent"]}
    except Exception:
        return None


@router.get("", response_model=DebugInfo)
def debug():
    return {
        "tab_url": browser.tab_url(),
        "renderer": browser.health(),
        "recent_calls": browser.recent_calls(),
        "webhooks": _webhook_status(),
        "note": "recent_calls is a 50-entry ring buffer of raw CDP calls "
                "(watchdog pings and stream drains included)",
    }
