"""Catalog surface: Apple Music's public side — search, browse, charts,
albums/artists/playlists and their relationships."""
import urllib.parse

from fastapi import APIRouter, HTTPException

from .. import musickit as mk
from ..browser import BrowserError

router = APIRouter(prefix="/catalog", tags=["catalog"])

STOREFRONT = "us"  # could become configurable later

CATALOG_RESOURCES = {"songs", "albums", "artists", "playlists", "music-videos",
                     "stations", "curators", "search-hints", "record-labels"}


@router.get("/search")
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


@router.get("/charts")
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


@router.get("/{resource}")
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


@router.get("/{resource}/{resource_id}")
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


@router.get("/{resource}/{resource_id}/{relationship}")
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
