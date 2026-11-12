"""TTL read cache + request coalescing for Apple amp-api GETs.

Design constraints — live-incident quirks, encoded so they stay true:

* Mutations are async (202/204) at Apple: the effect lands "a beat later",
  and callers verify with retried reads. So any mutation BUSTS the whole
  cache AND opens a short no-cache window (the "grace") — otherwise a
  retried read inside the async-apply window would cache the pre-mutation
  snapshot and serve it for a whole TTL, hiding the change that just
  happened.
* Bust is a superset on purpose. A heart IS a rating (value 1) and the
  three id spaces cross-link: ratings are keyed by CATALOG id, library
  removals by LIBRARY id, favorites accept both flavors, and playlist
  adds auto-add to the library. Per-key busting against that web is
  fragile; per-key bugs are silent (stale rows that look live). Any
  mutation busts everything — mutations are user-rare, reads are hot.
* Favorites auto-sync lags ~60s+ server-side, so the favorites/ratings
  families get a short TTL and reads can force freshness (`fresh=True`
  from routes, `?fresh=1` for clients).
* Flat, never recursive: one lock, one dict, single-flight via events.
  (The CDP layer died once from recursive reconnects — this module must
  never add nesting.)
"""
import logging
import os
import threading
import time

log = logging.getLogger("ampd.cache")

# after any mutation, GETs bypass the cache this long (async-apply window)
GRACE_S = 8.0
# bound the entry table so a 9k-song paginated export can't grow it forever
MAX_ENTRIES = 500


class ReadCache:
    """TTL cache + single-flight coalescing for GET reads. Thread-safe."""

    def __init__(self):
        self.base_ttl = float(os.environ.get("AMPD_CACHE_TTL", "30"))
        self.enabled = os.environ.get("AMPD_CACHE", "1") == "1" and self.base_ttl > 0
        self._entries = {}          # key -> (expires_at, value)
        self._inflight = {}         # key -> threading.Event
        self._waiters = {}          # key -> count of coalesced waiters
        self._blocked_until = 0.0   # grace window after a mutation
        self._lock = threading.Lock()

    # ------------------------------------------------------------- ttl rules

    def ttl_for(self, key):
        """Per-family TTL. Catalog data is public and near-static; favorites
        and ratings lag server-side (auto-sync ~60s+) so they get short TTLs."""
        if "/v1/catalog/" in key:
            return self.base_ttl * 10
        if "/v1/me/favorites" in key or "/v1/me/ratings" in key:
            return min(self.base_ttl, 10.0)
        return self.base_ttl

    # ------------------------------------------------------------- read path

    def get(self, key):
        if not self.enabled:
            return None
        with self._lock:
            entry = self._entries.get(key)
            if entry and entry[0] > time.time():
                return entry[1]
            if entry:
                self._entries.pop(key, None)      # expired
        return None

    def put(self, key, value):
        if not self.enabled:
            return
        with self._lock:
            self._entries[key] = (time.time() + self.ttl_for(key), value)
            if len(self._entries) > MAX_ENTRIES:
                self._evict_locked()

    def _evict_locked(self):
        now = time.time()
        for k in [k for k, (exp, _) in self._entries.items() if exp <= now]:
            self._entries.pop(k, None)
        while len(self._entries) > MAX_ENTRIES:
            self._entries.pop(next(iter(self._entries)))   # oldest inserted

    def coalesce(self, key, fetch, fresh=False, cache_when=None):
        """TTL cache + single-flight: identical in-flight GETs collapse into
        ONE upstream fetch; waiters share the leader's result. If the leader
        fails, a waiter re-fetches itself (no error caching). `cache_when`
        filters what gets stored (e.g. only HTTP 200s — never a 404/429)."""
        if not self.enabled or fresh or self.blocked():
            return fetch()
        hit = self.get(key)
        if hit is not None:
            return hit
        with self._lock:
            event = self._inflight.get(key)
            if event is None:
                event = threading.Event()
                self._inflight[key] = event
                leader = True
            else:
                leader = False
                self._waiters[key] = self._waiters.get(key, 0) + 1
        if leader:
            try:
                value = fetch()
                if cache_when is None or cache_when(value):
                    self.put(key, value)
                return value
            finally:
                with self._lock:
                    self._inflight.pop(key, None)
                    waiters = self._waiters.pop(key, 0)
                    event.set()
                if waiters:
                    log.info("coalesced: %s — 1 eval served %d waiter(s)",
                             key[:110], waiters)
        # follower: bounded wait for the leader's put, then read it
        event.wait(timeout=95)
        hit = self.get(key)
        if hit is not None:
            return hit
        return fetch()          # leader failed or entry evicted — go ourselves

    # ------------------------------------------------------- mutation hooks

    def blocked(self):
        """True inside the post-mutation grace window: GETs bypass cache."""
        with self._lock:
            return time.time() < self._blocked_until

    def after_mutation(self):
        """Call on EVERY mutation issue (async 202/204 included), BEFORE the
        request goes out: bust everything + open the grace window so the
        read-retry loops callers use can never be served stale cache."""
        with self._lock:
            self._entries.clear()
            self._blocked_until = time.time() + GRACE_S
        log.debug("cache busted + grace %.0fs (mutation)", GRACE_S)


# module-level singleton
read_cache = ReadCache()
