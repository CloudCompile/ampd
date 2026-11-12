"""Catalog surface: Apple Music's public side — search, browse, charts,
albums/artists/playlists and their relationships."""
import re
import urllib.parse
import html

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from .. import musickit as mk
from ..browser import BrowserError
from ..models import (ItemList, ItemRow, LibraryItem, Lyrics, RelationshipPage,
                      SearchHints)

router = APIRouter(prefix="/catalog", tags=["catalog"])

STOREFRONT = "us"  # could become configurable later

CATALOG_RESOURCES = {"songs", "albums", "artists", "playlists", "music-videos",
                     "stations", "curators", "search-hints", "record-labels"}


@router.get("/search", response_model=dict[str, list[ItemRow]])
def catalog_search(term: str, types: str = "songs,albums,artists,playlists",
                   limit: int = 10):
    """Multi-type catalog search. `types` is a comma list, e.g.
    songs,albums,artists,playlists,stations,curators,music-videos"""
    if not term:
        raise HTTPException(400, "term is required")
    try:
        data = mk.api_music(
            f"/v1/catalog/{STOREFRONT}/search?term={urllib.parse.quote(term)}"
            f"&types={types}&limit={min(limit, 25)}")
        out = {}
        for kind, group in (data.get("results", {}) or {}).items():
            out[kind] = [mk.item_row(t) for t in group.get("data", [])]
        return out
    except BrowserError as e:
        raise HTTPException(502, str(e))


@router.get("/hints", response_model=SearchHints)
def hints(term: str, types: str = "songs,artists,albums,playlists"):
    """Search suggestions (what the web player's autocomplete shows).
    Returns flat rows: {term/title, id, kind}."""
    if not term:
        raise HTTPException(400, "term is required")
    try:
        data = mk.api_music(
            f"/v1/catalog/{STOREFRONT}/search/suggestions?term={urllib.parse.quote(term)}"
            f"&kinds=topResults&types={types}")
        out = []
        for s in data.get("results", {}).get("suggestions", []):
            c = s.get("content") or {}
            if not c:
                continue
            out.append({"id": c.get("id"), "kind": c.get("type"),
                        "title": (c.get("attributes") or {}).get("name"),
                        "artist": (c.get("attributes") or {}).get("artistName")})
        return {"hints": out}
    except BrowserError as e:
        raise HTTPException(502, str(e))


def _ttml_time(s):
    """TTML begin/end stamp -> ms. Handles '12.345s' and 'H:MM:SS.mmm'."""
    if s.endswith("s"):
        s = s[:-1]
    parts = s.split(":")
    try:
        secs = float(parts[-1])
        if len(parts) == 3:
            secs += int(parts[0]) * 3600 + int(parts[1]) * 60
        elif len(parts) == 2:
            secs += int(parts[0]) * 60
        return int(secs * 1000)
    except ValueError:
        return None


def _parse_ttml(ttml):
    """TTML -> [{timeMs, text}]. Enough regex for Apple's flavor of TTML."""
    lines = []
    for m in re.finditer(r'<p[^>]*begin="([^"]+)"[^>]*>(.*?)</p>', ttml, re.S):
        text = re.sub(r"<[^>]+>", "", m.group(2))     # strip spans etc.
        text = html.unescape(text).strip()
        if text:
            lines.append({"timeMs": _ttml_time(m.group(1)), "text": text})
    return lines


@router.get("/songs/{song_id}/lyrics", response_model=Lyrics)
def song_lyrics(song_id: str, raw: bool = False):
    """Synced lyrics for a catalog song (Apple's TTML, parsed to lines).
    `raw=1` returns the raw TTML document. Songs without lyrics -> 404."""
    try:
        data = mk.api_music(f"/v1/catalog/{STOREFRONT}/songs/{song_id}/lyrics")
        attrs = (data.get("data") or [{}])[0].get("attributes", {})
        ttml = attrs.get("ttml")
        if not ttml:
            raise HTTPException(404, "no lyrics for this song")
        if raw:
            return Response(content=ttml, media_type="application/xml")
        return {"song_id": song_id, "lines": _parse_ttml(ttml)}
    except BrowserError as e:
        if "404" in str(e):
            raise HTTPException(404, "no lyrics for this song")
        raise HTTPException(502, str(e))


@router.get("/charts", response_model=dict[str, list[ItemRow]])
def charts(types: str = "songs", limit: int = 25, genre: str = None):
    """Catalog charts: most-played songs/albums/playlists. `genre` = genre id."""
    try:
        q = f"types={types}&limit={min(limit, 50)}"
        if genre:
            q += f"&genre={genre}"
        data = mk.api_music(f"/v1/catalog/{STOREFRONT}/charts?{q}")
        out = {}
        for kind, chart in (data.get("results", {}) or {}).items():
            out[kind] = [mk.item_row(t) for c in chart
                         for t in c.get("data", [])]
        return out
    except BrowserError as e:
        raise HTTPException(502, str(e))


@router.get("/{resource}", response_model=ItemList)
def catalog_by_ids(resource: str, ids: str):
    """Fetch specific catalog resources by (comma-separated) id."""
    if resource not in CATALOG_RESOURCES:
        raise HTTPException(404, f"unknown catalog resource {resource!r}. "
                                 f"Valid: {sorted(CATALOG_RESOURCES)}")
    try:
        data = mk.api_music(f"/v1/catalog/{STOREFRONT}/{resource}?ids={ids}")
        return {"items": [mk.item_row(t) for t in data.get("data", [])]}
    except BrowserError as e:
        raise HTTPException(502, str(e))


@router.get("/{resource}/{resource_id}", response_model=LibraryItem)
def catalog_item(resource: str, resource_id: str, extend: str = None):
    """One catalog item; `extend=tracks` etc. includes relationships inline."""
    if resource not in CATALOG_RESOURCES:
        raise HTTPException(404, f"unknown catalog resource {resource!r}. "
                                 f"Valid: {sorted(CATALOG_RESOURCES)}")
    try:
        q = f"extend={extend}" if extend else ""
        data = mk.api_music(
            f"/v1/catalog/{STOREFRONT}/{resource}/{resource_id}" + (f"?{q}" if q else ""))
        items = data.get("data", [])
        if not items:
            raise HTTPException(404, "not found in catalog")
        out = mk.item_row(items[0])
        out["relationships"] = items[0].get("relationships", {})
        return out
    except BrowserError as e:
        raise HTTPException(502, str(e))


@router.get("/{resource}/{resource_id}/{relationship}", response_model=RelationshipPage)
def catalog_relationship(resource: str, resource_id: str, relationship: str,
                         limit: int = 100, offset: int = 0):
    """e.g. /catalog/artists/{id}/albums, /catalog/albums/{id}/tracks."""
    try:
        data = mk.api_music(
            f"/v1/catalog/{STOREFRONT}/{resource}/{resource_id}/{relationship}"
            f"?limit={min(limit, 100)}&offset={offset}")
        return {"items": [mk.item_row(t) for t in data.get("data", [])],
                "next": data.get("next")}
    except BrowserError as e:
        raise HTTPException(502, str(e))
