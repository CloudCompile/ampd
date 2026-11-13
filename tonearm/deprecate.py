"""The freeze machinery (#50, #126, #127): deprecation policy enforcement
and the surface-version marker.

POLICY (docs/deprecation.md, the short version): an old shape or route
gets `Deprecation: true` + `Sunset:` headers for ONE MINOR CYCLE, then
dies. The error envelope (#32) is the last breaking change before the
freeze. This module is the enforcement half:

* DEPRECATED — the registry. Key: a path TEMPLATE as it appears in the
  OpenAPI (e.g. "/api/library/export"), value: {"sunset": "YYYY-MM-DD",
  "replacement": path-or-None, "note": str-or-None}. One entry per
  deprecated route; response-shape deprecations live in the changelog
  and get a sunset via the same registry when the shape has a route.
* stamp(response, path) — called by the deprecation middleware on every
  /api response; adds `Deprecation: true`, `Sunset:` (HTTP-date),
  `Deprecation-Note` and `Link: <...>; rel="successor-version"` when
  the route is in the registry. Everything else passes untouched.
* SURFACE_VERSION — major.minor of the package version, stamped on
  every /api response as `X-Tonearm-Surface` and on /health as the
  `surface` field, so clients can pin what they coded against.

Nothing is deprecated at freeze time — shipping the machinery first is
the point (#126): the policy exists BEFORE the first deprecation.
"""

from __future__ import annotations

import email.utils
import time
from datetime import date, datetime, timezone

# path template -> sunset details
DEPRECATED: dict[str, dict] = {}

# bumped by the same train as the package version (tonearm.__init__)
SURFACE_VERSION: str = ""          # set by init_surface() at import time


def init_surface(version: str) -> str:
    """major.minor of the package version — the pinnable surface."""
    global SURFACE_VERSION
    SURFACE_VERSION = ".".join(version.split(".")[:2]) or "0"
    return SURFACE_VERSION


def _http_date(iso: str) -> str:
    d = date.fromisoformat(iso)
    return email.utils.format_datetime(
        datetime(d.year, d.month, d.day, tzinfo=timezone.utc),
        usegmt=True)


def sunset_headers(path: str) -> dict[str, str]:
    """Deprecation headers for a path (empty when not deprecated)."""
    entry = DEPRECATED.get(path.rstrip("/")) or DEPRECATED.get(path)
    if not entry:
        return {}
    headers = {"Deprecation": "true",
               "Sunset": _http_date(entry["sunset"])}
    if entry.get("replacement"):
        headers["Link"] = (f'</api{entry["replacement"]}>; '
                           f'rel="successor-version"')
    if entry.get("note"):
        headers["Deprecation-Note"] = entry["note"]
    return headers


def stamp(response, path: str, surface: str | None = None) -> None:
    """Stamp one response with surface + deprecation headers (if any)."""
    surface = surface or SURFACE_VERSION
    if surface:
        response.headers.setdefault("X-Tonearm-Surface", surface)
    for k, v in sunset_headers(path).items():
        response.headers.setdefault(k, v)


def is_live(entry: dict, now: float | None = None) -> bool:
    """True while the sunset date is still in the future."""
    if now is None:
        now = time.time()
    return date.fromisoformat(entry["sunset"]).toordinal() > \
        time.gmtime(now).tm_year * 10000 + time.gmtime(now).tm_mon * 100 \
        + time.gmtime(now).tm_mday
