"""GET /api/debug — an operator's window into the CDP layer.

Rule (learned via /health hanging once): a debug surface must NEVER eval the
renderer it is diagnosing. Everything here reads state already held in
memory or the socket-free Chrome HTTP API:
  * last-N CDP calls with durations (ring buffer in browser._raw_call)
  * current music-tab URL (chrome /json/list — HTTP, not an eval)
  * renderer health snapshot (the watchdog's own dict)
Gated behind AMPD_API_KEY when set (it sits under /api like everything else).
"""
from fastapi import APIRouter

from ..browser import browser
from ..models import DebugInfo

router = APIRouter(prefix="/debug", tags=["debug"])


@router.get("", response_model=DebugInfo)
def debug():
    return {
        "tab_url": browser.tab_url(),
        "renderer": browser.health(),
        "recent_calls": browser.recent_calls(),
        "note": "recent_calls is a 50-entry ring buffer of raw CDP calls "
                "(watchdog pings and stream drains included)",
    }
