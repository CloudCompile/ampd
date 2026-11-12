"""Personal / personalized surface: For You, listening history, radio."""
from fastapi import APIRouter, HTTPException

from .. import musickit as mk
from ..browser import BrowserError
from ..models import ItemList, MadeForYou, Recommendations

router = APIRouter(prefix="/personal", tags=["personal"])


@router.get("/recommendations", response_model=Recommendations)
def recommendations():
    """'Listen Now' / For You recommendations (albums & playlists, grouped)."""
    try:
        data = mk.api_music("/v1/me/recommendations")
        groups = []
        for rec in data.get("data", []):
            attrs = rec.get("attributes", {}) or {}
            rels = rec.get("relationships", {}) or {}
            groups.append({
                "id": rec.get("id"),
                "title": attrs.get("title", {}).get("string") if isinstance(attrs.get("title"), dict) else attrs.get("title"),
                "reason": attrs.get("reason"),
                "items": [mk.item_row(t) for rel in rels.values()
                          for t in rel.get("data", [])],
            })
        return {"groups": [g for g in groups if g["items"]]}
    except BrowserError as e:
        raise HTTPException(502, str(e))


@router.get("/heavy-rotation", response_model=ItemList)
def heavy_rotation():
    """Albums and playlists you've had in heavy rotation."""
    try:
        data = mk.api_music("/v1/me/history/heavy-rotation")
        return {"items": [mk.item_row(t) for t in data.get("data", [])]}
    except BrowserError as e:
        raise HTTPException(502, str(e))


@router.get("/recently-played", response_model=ItemList)
def recently_played(limit: int = 20):
    """Your recently played items (Apple caps this at 20)."""
    try:
        data = mk.api_music(f"/v1/me/recent/played?limit={min(limit, 20)}")
        return {"items": [mk.item_row(t) for t in data.get("data", [])]}
    except BrowserError as e:
        raise HTTPException(502, str(e))


@router.get("/made-for-you", response_model=MadeForYou)
def made_for_you():
    """Apple's auto-generated personal playlists (Favorites Mix, New Music…)."""
    try:
        data = mk.api_music("/v1/me/library/playlists?limit=100")
        # personal mixes live in the library under predictable names; surface
        # playlists whose source is Apple's made-for-you engine
        pls = [mk.item_row(t) for t in data.get("data", [])]
        mixes = [p for p in pls
                 for a in [p.get("attributes", {})]
                 if a.get("playlistType") == "M3U_STREAM" or "Mix" in (a.get("name") or "")]
        return {"playlists": mixes}
    except BrowserError as e:
        raise HTTPException(502, str(e))
