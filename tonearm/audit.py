"""The per-key audit log (v0.7 #47, #120).

Every AUTHENTICATED mutating request lands here: ts, key, method, path,
status. Two stores, one contract:

* the local store's `audit` table (v3) — durable, exportable, the
  source of truth when TONEARM_STORE=1;
* an in-memory ring (last RING=1000) — the export source when the store
  is OFF (stated honestly in the route's response).

Request BODIES are never recorded — a playlist name is the user's
business. Master-only export: friends don't audit each other.
"""
import collections
import threading
import time

from .store import StoreDisabled, store

RING = 1000

_ring: collections.deque = collections.deque(maxlen=RING)
_lock = threading.Lock()


def record(identity, method, path, status):
    """One authenticated mutation. Never raises — the audit trail must
    not become the request path's failure mode."""
    entry = {"ts": time.time(), "key_id": identity.key_id,
             "method": method, "path": path, "status": status}
    with _lock:
        _ring.append(entry)
    try:
        store.audit_append([(entry["ts"], entry["key_id"], entry["method"],
                             entry["path"], entry["status"])])
    except StoreDisabled:
        pass                                  # ring-only mode — stated
    except Exception as e:
        import logging
        logging.getLogger("tonearm.audit").warning(
            "audit flush failed (kept): %s", e)
    return entry


def export(since=0.0, limit=200, offset=0):
    """Who did what, newest first. Store-backed when possible; the ring
    (last 1000, this boot) otherwise — the response says which."""
    try:
        out = store.audit_since(since=since, limit=limit, offset=offset)
        out["source"] = "store"
        return out
    except StoreDisabled:
        with _lock:
            rows = [e for e in _ring if e["ts"] > since]
        rows.sort(key=lambda e: e["ts"], reverse=True)
        total = len(rows)
        rows = rows[offset:offset + limit]
        return {"total": total, "count": len(rows), "items": rows,
                "next_offset": offset + len(rows)
                if offset + len(rows) < total and rows else None,
                "source": "ring (store off — last 1000, this boot)"}
