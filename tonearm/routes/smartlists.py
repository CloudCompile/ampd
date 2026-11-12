"""Smart-playlist engine surface (v0.6 #44).

The engine lives in `tonearm/smartlists.py`; this router is CRUD + preview +
refresh. Everything requires the local store (evaluation IS the store —
there is nothing to serve without it: honest 501 `store_disabled`).
Materialization additionally answers 501 `writes_disabled` until
TONEARM_ENABLE_WRITES=1 — evaluation never touches Apple either way.

Routes:
  GET    /api/smartlists                     definitions + last sync state
  POST   /api/smartlists                     create (rules validated, 400 on junk)
  GET    /api/smartlists/{id}                one definition
  PATCH  /api/smartlists/{id}                partial update
  DELETE /api/smartlists/{id}                delete the definition (the Apple
                                             playlist, if one was materialized,
                                             is left alone — you keep the music)
  GET    /api/smartlists/{id}/preview        evaluate NOW, locally, no Apple
  POST   /api/smartlists/{id}/refresh        evaluate + materialize (full PUT)
"""
import uuid

from fastapi import APIRouter

from .. import smartlists as engine
from ..errors import ApiError
from ..models import (Ok, Smartlist, SmartlistCreate, SmartlistPreview,
                      SmartlistRefresh, Smartlists, SmartlistUpdate)
from ..store import StoreDisabled, store

router = APIRouter(prefix="/smartlists", tags=["smartlists (automation)"])


def _disabled(e):
    return ApiError(501, "store_disabled", str(e))


def _writes_disabled(e):
    return ApiError(501, "writes_disabled", str(e))


def _not_found(list_id):
    return ApiError(404, "not_found",
                    f"no smartlist with id {list_id!r}")


def _get_or_404(list_id):
    try:
        sl = store.smartlist_get(list_id)
    except StoreDisabled as e:
        raise _disabled(e)
    if sl is None:
        raise _not_found(list_id)
    return sl


@router.get("", response_model=Smartlists)
def list_smartlists():
    """All smart-playlist definitions with their last evaluation/sync state."""
    try:
        return {"enabled": True, "items": store.smartlist_rows(),
                "scheduler_interval": engine.config.smartlist_interval}
    except StoreDisabled as e:
        raise _disabled(e)


@router.post("", response_model=Smartlist)
def create_smartlist(body: SmartlistCreate):
    """Define a smart playlist. Rules are validated eagerly — a bad rule is
    a 400 here, never a silent empty list later."""
    try:
        rules = engine.validate_rules(body.rules or [])
        sort = engine.validate_sort(body.sort or "added_desc")
    except engine.SmartlistError as e:
        raise ApiError(400, "bad_rule", str(e))
    list_id = engine.new_list_id()
    try:
        store.smartlist_add(list_id, body.name,
                            body.description or "", rules, sort,
                            max(0, body.limit or 0),
                            max(0, body.refresh_s or 0))
        return store.smartlist_get(list_id)
    except StoreDisabled as e:
        raise _disabled(e)


@router.get("/{list_id}", response_model=Smartlist)
def get_smartlist(list_id: str):
    return _get_or_404(list_id)


@router.patch("/{list_id}", response_model=Smartlist)
def update_smartlist(list_id: str, body: SmartlistUpdate):
    """Partial update. Replaces whichever fields are present; rules are
    re-validated in full whenever they appear."""
    _get_or_404(list_id)
    fields = body.model_dump(exclude_unset=True)
    if "rules" in fields:
        try:
            fields["rules"] = engine.validate_rules(fields["rules"] or [])
        except engine.SmartlistError as e:
            raise ApiError(400, "bad_rule", str(e))
    if "sort" in fields and fields["sort"] is not None:
        try:
            fields["sort"] = engine.validate_sort(fields["sort"])
        except engine.SmartlistError as e:
            raise ApiError(400, "bad_rule", str(e))
    if "limit" in fields and fields["limit"] is not None:
        fields["limit_n"] = max(0, fields.pop("limit"))
    if "refresh_s" in fields and fields["refresh_s"] is not None:
        fields["refresh_s"] = max(0, fields["refresh_s"])
    try:
        store.smartlist_update(list_id, **fields)
        return store.smartlist_get(list_id)
    except (StoreDisabled, ValueError) as e:
        raise ApiError(400, "bad_request", str(e))


@router.delete("/{list_id}", response_model=Ok)
def delete_smartlist(list_id: str):
    _get_or_404(list_id)
    try:
        store.smartlist_delete(list_id)
    except StoreDisabled as e:
        raise _disabled(e)
    return {"ok": True, "note": "definition deleted; any materialized "
                                "Apple playlist was left alone"}


@router.get("/{list_id}/preview", response_model=SmartlistPreview)
def preview(list_id: str):
    """The evaluation, served from the store — no Apple calls at all."""
    sl = _get_or_404(list_id)
    try:
        rows = store.library_rows()
        lp = engine.last_played_index(store)
        matched = engine.sort_rows(
            engine.evaluate(rows, sl["rules"], last_played=lp),
            sl.get("sort"))
        cap = sl.get("limit") or 0
        items = matched[:cap] if cap else matched
        return {"id": sl["id"], "name": sl["name"], "total": len(matched),
                "count": len(items), "items": items}
    except StoreDisabled as e:
        raise _disabled(e)


@router.post("/{list_id}/refresh", response_model=SmartlistRefresh)
def refresh(list_id: str):
    """Evaluate + materialize: find-or-create the live playlist, then one
    full-list PUT so Apple matches the evaluation exactly. Requires
    TONEARM_ENABLE_WRITES=1 (evaluation-only? use /preview)."""
    sl = _get_or_404(list_id)
    try:
        return engine.materialize_list(sl)
    except engine.SmartlistWritesDisabled as e:
        raise _writes_disabled(e)
    except StoreDisabled as e:
        raise _disabled(e)
