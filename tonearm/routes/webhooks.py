"""Outbound webhook management (v0.6 Automation).

The engine lives in `tonearm/webhooks.py`; this router is the configuration
surface. All of it answers an honest 501 when `TONEARM_WEBHOOKS` is unset,
and every response redacts secrets (`has_secret`, never the secret itself).

Routes:
  GET    /api/webhooks                 hooks + pending + recent deliveries
  POST   /api/webhooks                 add a hook (same URL updates it)
  PATCH  /api/webhooks/{id}            change url/events/secret/enabled
  DELETE /api/webhooks/{id}            remove a hook
  POST   /api/webhooks/{id}/test       synchronous one-shot delivery
  GET    /api/webhooks/deliveries      recent delivery attempts
"""
from fastapi import APIRouter

from .. import webhooks
from ..errors import ApiError
from ..models import (Ok, WebhookCreate, WebhookDeliveries, WebhookHook,
                      WebhookList, WebhookTest, WebhookUpdate)

router = APIRouter(prefix="/webhooks", tags=["webhooks (automation)"])


def _disabled(e):
    return ApiError(501, "webhooks_disabled", str(e))


def _not_found(hook_id):
    return ApiError(404, "not_found", f"no webhook with id {hook_id!r}")


@router.get("", response_model=WebhookList)
def list_hooks():
    """Configured hooks (secrets redacted), pending deliveries and the last
    few attempts. Delivery is at-least-once; consumers dedupe on event `id`."""
    try:
        return webhooks.snapshot()
    except webhooks.WebhooksDisabled as e:
        raise _disabled(e)


@router.get("/deliveries", response_model=WebhookDeliveries)
def list_deliveries(limit: int = 50):
    """The last N delivery attempts (newest first), retries included."""
    try:
        return webhooks.deliveries(limit=limit)
    except webhooks.WebhooksDisabled as e:
        raise _disabled(e)


@router.post("", response_model=WebhookHook)
def create_hook(body: WebhookCreate):
    """Add a webhook. `events` is an optional filter (empty = everything);
    `secret` enables HMAC-SHA256 signing. Adding an existing URL updates it."""
    try:
        return webhooks.add_hook(body.url, events=body.events,
                                 secret=body.secret, enabled=body.enabled)
    except webhooks.WebhooksDisabled as e:
        raise _disabled(e)
    except ValueError as e:
        raise ApiError(400, "bad_request", str(e))


@router.patch("/{hook_id}", response_model=WebhookHook)
def update_hook(hook_id: str, body: WebhookUpdate):
    """Partial update. Omitted fields stay as they are; `secret: ""` clears
    the signing secret."""
    fields = body.model_dump(exclude_unset=True)
    try:
        hook = webhooks.update_hook(hook_id, **fields)
    except webhooks.WebhooksDisabled as e:
        raise _disabled(e)
    except ValueError as e:
        raise ApiError(400, "bad_request", str(e))
    if hook is None:
        raise _not_found(hook_id)
    return hook


@router.delete("/{hook_id}", response_model=Ok)
def delete_hook(hook_id: str):
    """Remove a hook. Already-queued deliveries for it still go out."""
    try:
        removed = webhooks.remove_hook(hook_id)
    except webhooks.WebhooksDisabled as e:
        raise _disabled(e)
    if not removed:
        raise _not_found(hook_id)
    return {"ok": True}


@router.post("/{hook_id}/test", response_model=WebhookTest)
def test_hook(hook_id: str):
    """Deliver a `webhook.test` event right now and report the result.
    No background retry — this is a diagnostic, not an event."""
    try:
        result = webhooks.test_hook(hook_id)
    except webhooks.WebhooksDisabled as e:
        raise _disabled(e)
    if result is None:
        raise _not_found(hook_id)
    return result
