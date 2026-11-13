"""API keys — the multi-user auth core (v0.7, #46).

The model, stated plainly:

* `TONEARM_API_KEY` (the legacy env) remains the MASTER key: all scopes,
  no rate ceiling. It bootstraps everything else. If it's unset, the
  server runs keyless exactly as before — multi-key is opt-in by
  creating keys.
* Additional keys live in a 0600 JSON file (`keys.json`, next to the
  store db). The file stores HASHES (sha256) — a leaked keys file must
  not leak keys. A raw key is shown exactly once, at creation
  (`python -m tonearm keys add`).
* **Scopes**: `read` (GETs) and `write` (everything else — every
  mutation, playback control included; a friend's UI watches, yours
  drives). `write` implies `read`.
* **Rate ceilings**: per-key, sliding 60s window, in memory — 429 with
  `Retry-After` when exceeded. The master key is never limited. Ceiling
  0 = unlimited.
* **SSE caps**: per-key concurrent /api/stream connections (default 3) —
  a browser tab family is a few connections; a fleet of tabs is abuse.
  Master unlimited.

The registry is loaded at import and re-read on miss (a CLI `keys add`
takes effect without restarting the server).
"""
import hashlib
import json
import logging
import os
import secrets
import threading
import time

from .config import config
from .metrics import METRICS

log = logging.getLogger("tonearm.keys")

READ = "read"
WRITE = "write"
SCOPES = (READ, WRITE)
DEFAULT_SSE_CAP = 3


def hash_key(raw):
    return hashlib.sha256(raw.encode()).hexdigest()


def new_raw_key():
    return "toneark_" + secrets.token_urlsafe(24)


class AuthIdentity:
    """What auth_guard knows after resolving a presented key."""

    def __init__(self, key_id, name, scopes, rate, is_master=False):
        self.key_id = key_id
        self.name = name
        self.scopes = frozenset(scopes)
        self.rate = rate                      # req/min, 0 = unlimited
        self.is_master = is_master

    @property
    def can_read(self):
        return True                           # every key can read; even keyless

    @property
    def can_write(self):
        return WRITE in self.scopes

    def describe(self):
        return "master" if self.is_master else self.key_id


MASTER = AuthIdentity("master", "master", (READ, WRITE), 0, is_master=True)
ANON = AuthIdentity("none", "anonymous", (READ,), 0)


class KeysRegistry:
    """The keys file, in memory. Re-read when a presented key isn't found —
    the CLI writes the file, the server picks it up without a restart."""

    def __init__(self, path=None):
        self.path = path or config.keys_file_path()
        self._lock = threading.RLock()   # reentrant: add() holds it while
        self._cache = None               # _save() refreshes the cache
        self._mtime = 0

    def _load(self):
        """The parsed registry, cached by mtime. Missing file = no keys
        (keyless/master-only mode)."""
        with self._lock:
            try:
                mtime = os.path.getmtime(self.path)
            except OSError:
                self._cache, self._mtime = [], 0
                return self._cache
            if self._cache is not None and mtime == self._mtime:
                return self._cache
            try:
                data = json.load(open(self.path))
                self._cache = [k for k in data.get("keys", []) if k.get("id")]
                self._mtime = mtime
            except (json.JSONDecodeError, OSError) as e:
                log.warning("keys file unreadable (%s) — treating as empty", e)
                self._cache, self._mtime = [], 0
        return self._cache

    def _save(self, keys):
        """Atomic write, 0600 — same discipline as the webhooks file."""
        d = os.path.dirname(self.path)
        if d:
            os.makedirs(d, exist_ok=True)
            try:
                os.chmod(d, 0o700)
            except OSError:
                pass
        tmp = self.path + ".tmp"
        with open(tmp, "w") as f:
            json.dump({"keys": keys}, f, indent=1)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, self.path)
        os.chmod(self.path, 0o600)
        with self._lock:
            self._cache, self._mtime = keys, os.path.getmtime(self.path)

    # ----------------------------------------------------------- resolution

    def resolve(self, raw_key):
        """Presented raw key -> AuthIdentity | None. Re-reads the file on
        a miss so `keys add` lands without a restart."""
        if not raw_key:
            return None
        if config.api_key and raw_key == config.api_key:
            return MASTER
        h = hash_key(raw_key)
        for k in self._load():
            if k.get("key_hash") == h and not k.get("revoked"):
                return AuthIdentity(k["id"], k.get("name") or k["id"],
                                    k.get("scopes") or (READ,),
                                    k.get("rate") or 0)
        # miss: the file may have changed since our cache was read
        self._cache, self._mtime = None, 0
        for k in self._load():
            if k.get("key_hash") == h and not k.get("revoked"):
                return AuthIdentity(k["id"], k.get("name") or k["id"],
                                    k.get("scopes") or (READ,),
                                    k.get("rate") or 0)
        return None

    def has_keys(self):
        return bool(self._load())

    # --------------------------------------------------------------- CRUD

    def add(self, name, scopes=(READ,), rate=0):
        """Create a key. Returns (key_id, raw_key) — the raw key is shown
        ONCE; only its hash is stored."""
        for s in scopes:
            if s not in SCOPES:
                raise ValueError(f"unknown scope {s!r} — known: {SCOPES}")
        raw = new_raw_key()
        kid = "k-" + secrets.token_hex(4)
        with self._lock:
            keys = list(self._load())
            if any(k.get("name") == name for k in keys):
                raise ValueError(f"a key named {name!r} already exists")
            keys.append({"id": kid, "name": name, "key_hash": hash_key(raw),
                         "scopes": list(scopes), "rate": rate,
                         "created_at": time.time()})
            self._save(keys)
        METRICS.gauge("tonearm_keys_active", len(keys),
                      help_text="API keys in the registry")
        return kid, raw

    def list(self):
        return [{"id": k["id"], "name": k.get("name"),
                 "scopes": k.get("scopes"), "rate": k.get("rate") or 0,
                 "created_at": k.get("created_at"),
                 "revoked": bool(k.get("revoked"))}
                for k in self._load()]

    def revoke(self, key_id):
        with self._lock:
            keys = list(self._load())
            for k in keys:
                if k["id"] == key_id:
                    if k.get("revoked"):
                        return False          # already dead — say so
                    k["revoked"] = time.time()
                    self._save(keys)
                    return True
        return False


# ------------------------------------------------------------- rate limit
# sliding 60s window per key id, in memory. Deliberately NOT distributed —
# one server, one lock, honest ceilings for friends.

class RateLimiter:
    WINDOW_S = 60.0

    def __init__(self):
        self._hits: dict[str, list[float]] = {}
        self._lock = threading.Lock()

    def check(self, identity):
        """True = allowed. A hit is recorded even when it exceeds (fail
        closed counts), Retry-After = the window's reset."""
        if identity.is_master or not identity.rate:
            return True, 0
        now = time.time()
        with self._lock:
            hits = [t for t in self._hits.get(identity.key_id, [])
                    if now - t < self.WINDOW_S]
            allowed = len(hits) < identity.rate
            hits.append(now)
            self._hits[identity.key_id] = hits
            if not allowed:
                oldest = hits[0]
                retry = int(self.WINDOW_S - (now - oldest)) + 1
                METRICS.inc("tonearm_rate_limited_total",
                            {"key": identity.key_id},
                            help_text="requests rejected by a per-key ceiling")
                return False, max(1, retry)
        return True, 0


class SseCap:
    """Per-key concurrent /api/stream connections (#118)."""

    def __init__(self):
        self._count: dict[str, int] = {}
        self._lock = threading.Lock()

    def enter(self, identity):
        if identity.is_master:
            return True
        cap = int(os.environ.get("TONEARM_SSE_CAP", DEFAULT_SSE_CAP))
        with self._lock:
            n = self._count.get(identity.key_id, 0)
            if n >= cap:
                METRICS.inc("tonearm_sse_capped_total",
                            {"key": identity.key_id},
                            help_text="SSE connections rejected by the "
                                      "per-key cap")
                return False
            self._count[identity.key_id] = n + 1
            return True

    def leave(self, identity):
        if identity.is_master:
            return
        with self._lock:
            n = self._count.get(identity.key_id, 0)
            if n <= 1:
                self._count.pop(identity.key_id, None)
            else:
                self._count[identity.key_id] = n - 1


registry = KeysRegistry()
limiter = RateLimiter()
sse_cap = SseCap()


# --------------------------------------------------------------- the CLI

def main():
    """python -m tonearm keys add|list|revoke"""
    import argparse
    p = argparse.ArgumentParser(prog="tonearm keys")
    sub = p.add_subparsers(dest="cmd", required=True)
    add = sub.add_parser("add", help="create a key (the raw key is shown ONCE)")
    add.add_argument("name")
    add.add_argument("--scopes", default="read",
                     help="comma list: read | read,write")
    add.add_argument("--rate", type=int, default=0,
                     help="requests/minute ceiling (0 = unlimited)")
    sub.add_parser("list", help="list keys (hashes never shown)")
    rev = sub.add_parser("revoke", help="revoke a key by id")
    rev.add_argument("key_id")
    args = p.parse_args()

    if args.cmd == "add":
        scopes = [s.strip() for s in args.scopes.split(",") if s.strip()]
        if "write" in scopes and "read" not in scopes:
            scopes.append("read")             # write implies read
        kid, raw = registry.add(args.name, tuple(scopes), args.rate)
        print(f"key created: {kid} ({args.name}, scopes={','.join(scopes)}, "
              f"rate={args.rate or 'unlimited'}/min)")
        print(f"\n  {raw}\n")
        print("Store it NOW — only its hash is kept; this is the only time "
              "it is shown.")
    elif args.cmd == "list":
        for k in registry.list():
            state = "REVOKED" if k["revoked"] else "active"
            print(f"{k['id']}  {k['name'] or '-':16} "
                  f"scopes={','.join(k['scopes'] or []):12} "
                  f"rate={k['rate'] or 'unltd'}  {state}")
    elif args.cmd == "revoke":
        print("revoked" if registry.revoke(args.key_id)
              else f"no key {args.key_id!r}")


if __name__ == "__main__":
    main()
