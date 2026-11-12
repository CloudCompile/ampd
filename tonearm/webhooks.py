"""Outbound webhooks (v0.6 Automation #88) — opt-in, zero new deps.

Apple has no webhooks. tonearm can be the webhook: the events the server
already observes (the stream-hook buffer, write routes, the renderer
watchdog, the library snapshot walk) are POSTed to user-configured URLs.

Design:

* **One event bus, many producers.** Producers call `emit(type, data)` and
  never know whether anyone is listening. Emitting is a dict append when the
  feature is off — it can never slow a request or a background walk.
* **Delivery is decoupled and bounded.** A single daemon worker owns a
  time-ordered retry heap. Producers never wait on HTTP, and one dead
  receiver can't stall another. Pending deliveries are in memory: a restart
  drops them (documented honestly — a durable outbox would need the store).
* **Retries with backoff, not blind loops.** Network errors, timeouts, 429
  and 5xx retry (2s, 10s, 30s, 120s, 600s by default); other 4xx are dead
  letters — retrying a 400 forever is how you become a spammer.
* **Secrets never leave the server.** `GET /api/webhooks` reports
  `has_secret`, not the secret. Signed deliveries carry
  `X-Tonearm-Signature: sha256=<hex HMAC of the raw body>`.
* **Config is a 0600 JSON file on the volume**, managed through
  `/api/webhooks` (or hand-edited while the server is stopped). One hook per
  URL — adding the same URL again updates it instead of duplicating.

Event types are stable strings (see `EVENT_TYPES`); a hook with an empty
`events` list receives everything.
"""
import hashlib
import heapq
import hmac
import json
import logging
import os
import secrets
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from collections import deque

from . import __version__
from .config import config
from .metrics import METRICS

log = logging.getLogger("tonearm.webhooks")

# ---- the event vocabulary (stable; empty filter = all) -------------------
TRACK_CHANGE = "track.change"
PLAYBACK_PAUSED = "playback.paused"
PLAYBACK_RESUMED = "playback.resumed"
FAVORITE_ADDED = "favorite.added"
FAVORITE_REMOVED = "favorite.removed"
RATING_CHANGED = "rating.changed"
LIBRARY_ADDED = "library.added"
LIBRARY_REMOVED = "library.removed"
LIBRARY_ALBUM_ADDED = "library.album.added"
LIBRARY_ALBUM_REMOVED = "library.album.removed"
LIBRARY_CHANGED = "library.changed"
LIBRARY_DEDUPED = "library.deduped"
LIBRARY_RATED = "library.rated"
PLAYLIST_CREATED = "playlist.created"
PLAYLIST_TRACKS_ADDED = "playlist.tracks.added"
PLAYLIST_TRACKS_REPLACED = "playlist.tracks.replaced"
PLAYLIST_RENAMED = "playlist.renamed"
PLAYLIST_DELETED = "playlist.deleted"
PLAYLIST_RESTORED = "playlist.restored"
RENDERER_STALLED = "renderer.stalled"
RENDERER_RECOVERED = "renderer.recovered"
SWEEP_DIGEST = "sweep.digest"
WEBHOOK_TEST = "webhook.test"
RELEASE_FOUND = "release.found"
SMARTLIST_UPDATED = "smartlist.updated"

EVENT_TYPES = frozenset({
    TRACK_CHANGE, PLAYBACK_PAUSED, PLAYBACK_RESUMED,
    FAVORITE_ADDED, FAVORITE_REMOVED, RATING_CHANGED,
    LIBRARY_ADDED, LIBRARY_REMOVED, LIBRARY_ALBUM_ADDED,
    LIBRARY_ALBUM_REMOVED, LIBRARY_CHANGED, LIBRARY_DEDUPED, LIBRARY_RATED,
    PLAYLIST_CREATED, PLAYLIST_TRACKS_ADDED, PLAYLIST_TRACKS_REPLACED,
    PLAYLIST_RENAMED, PLAYLIST_DELETED, PLAYLIST_RESTORED,
    RENDERER_STALLED, RENDERER_RECOVERED, SWEEP_DIGEST, WEBHOOK_TEST,
    RELEASE_FOUND, SMARTLIST_UPDATED,
})

# statuses worth trying again; every other 4xx is a dead letter
RETRYABLE_STATUS = frozenset({408, 425, 429})
DEFAULT_BACKOFF_S = (2, 10, 30, 120, 600)


class WebhooksDisabled(RuntimeError):
    """Raised by the management surface when TONEARM_WEBHOOKS is off; routes
    map it to an honest 501."""


def iso_now():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def sign(secret, body, ts=None):
    """The signature contract: hex HMAC-SHA256 over the exact request body
    (prefixed with `X-Tonearm-Timestamp` + '.' when a ts is given, so a
    receiver can also enforce freshness). Compare against
    `X-Tonearm-Signature: sha256=<hex>`."""
    if isinstance(body, str):
        body = body.encode()
    if ts is not None:
        body = f"{ts}.".encode() + body
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def make_event(event_type, data=None):
    """The one payload shape. `id` is stable across retries; consumers can
    dedupe on it (at-least-once delivery is the contract)."""
    return {"id": "evt_" + uuid.uuid4().hex,
            "type": event_type,
            "created_at": iso_now(),
            "tonearm_version": __version__,
            "data": data or {}}


def hook_accepts(hook, event_type):
    """Enabled + (no filter or the event is listed)."""
    if not hook.get("enabled", True):
        return False
    events = hook.get("events") or []
    return not events or event_type in events


def _normalize_events(events):
    if events is None:
        return []
    if not isinstance(events, (list, tuple)):
        raise ValueError("events must be a list of event type strings")
    if "*" in events:
        return []
    unknown = sorted(set(events) - EVENT_TYPES)
    if unknown:
        raise ValueError(f"unknown event type(s): {', '.join(unknown)}")
    return sorted(set(events))


def _validate_url(url):
    if not isinstance(url, str) or not url.strip():
        raise ValueError("url is required")
    url = url.strip()
    if len(url) > 2048:
        raise ValueError("url is too long (max 2048)")
    parts = urllib.parse.urlsplit(url)
    if parts.scheme not in ("http", "https") or not parts.netloc:
        raise ValueError("url must be an absolute http:// or https:// URL")
    return url


# ------------------------------------------------------------- registry
# The hook list + per-hook delivery stats. Persisted atomically as 0600 JSON;
# the stats are process-local (they reset on restart, like the pending heap).

class WebhookRegistry:
    def __init__(self, path=None):
        self.path = path or config.webhooks_config_path()
        self._lock = threading.Lock()
        self._hooks = []
        self._stats = {}

    # -- persistence --

    def load(self):
        try:
            with open(self.path) as f:
                payload = json.load(f)
        except FileNotFoundError:
            return self
        except Exception as e:
            log.warning("webhooks: could not read %s (%s) — starting empty",
                        self.path, e)
            return self
        hooks = payload.get("hooks") if isinstance(payload, dict) else None
        if not isinstance(hooks, list):
            log.warning("webhooks: %s has no hooks list — starting empty",
                        self.path)
            return self
        clean = []
        for h in hooks:
            try:
                url = _validate_url(h.get("url"))
            except ValueError:
                continue
            clean.append({"id": h.get("id") or _new_hook_id(),
                          "url": url,
                          "events": _normalize_events(h.get("events")),
                          "secret": h.get("secret") or None,
                          "enabled": bool(h.get("enabled", True)),
                          "created_at": h.get("created_at") or time.time()})
        with self._lock:
            self._hooks = clean
        log.info("webhooks: loaded %d hook(s) from %s", len(clean), self.path)
        return self

    def _save_locked(self):
        directory = os.path.dirname(self.path) or "."
        os.makedirs(directory, exist_ok=True)
        tmp = f"{self.path}.tmp-{os.getpid()}"
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as f:
            json.dump({"hooks": self._hooks}, f, indent=1)
        os.chmod(tmp, 0o600)                 # enforce even with a loose umask
        os.replace(tmp, self.path)
        try:
            os.chmod(self.path, 0o600)
        except OSError:
            pass

    # -- reads --

    def count(self):
        with self._lock:
            return len(self._hooks)

    def get(self, hook_id):
        with self._lock:
            for h in self._hooks:
                if h["id"] == hook_id:
                    return dict(h)
        return None

    def matching(self, event_type):
        now = time.time()
        with self._lock:
            return [dict(h) for h in self._hooks
                    if hook_accepts(h, event_type)
                    and not (self._stats.get(h["id"], {}).get("parked_until")
                             or 0) > now]

    def public_hooks(self):
        with self._lock:
            return [self._public(h) for h in self._hooks]

    def _public(self, hook):
        stats = dict(self._stats.get(hook["id"], {}))
        parked_until = stats.get("parked_until")
        return {"id": hook["id"], "url": hook["url"],
                "events": list(hook.get("events") or []),
                "enabled": bool(hook.get("enabled", True)),
                "has_secret": bool(hook.get("secret")),
                "created_at": hook.get("created_at"),
                "stats": {"delivered": stats.get("delivered", 0),
                          "failed": stats.get("failed", 0),
                          "dead_letters": stats.get("dead_letters", 0),
                          "parked": bool(parked_until and
                                         parked_until > time.time()),
                          "parked_until": parked_until,
                          "last_status": stats.get("last_status"),
                          "last_error": stats.get("last_error"),
                          "last_attempt_at": stats.get("last_attempt_at")}}

    # -- writes --

    def add(self, url, events=None, secret=None, enabled=True):
        url = _validate_url(url)
        events = _normalize_events(events)
        secret = secret or None
        with self._lock:
            existing = next((h for h in self._hooks if h["url"] == url), None)
            if existing is not None:
                existing.update({"events": events, "enabled": bool(enabled)})
                if secret is not None:
                    existing["secret"] = secret
                self._save_locked()
                return self._public(existing)
            hook = {"id": _new_hook_id(), "url": url, "events": events,
                    "secret": secret, "enabled": bool(enabled),
                    "created_at": time.time()}
            self._hooks.append(hook)
            self._save_locked()
            return self._public(hook)

    def update(self, hook_id, url=None, events=None, secret=None,
               enabled=None):
        with self._lock:
            hook = next((h for h in self._hooks if h["id"] == hook_id), None)
            if hook is None:
                return None
            if url is not None:
                hook["url"] = _validate_url(url)
            if events is not None:
                hook["events"] = _normalize_events(events)
            if secret is not None:
                hook["secret"] = secret or None
            if enabled is not None:
                hook["enabled"] = bool(enabled)
            self._save_locked()
            return self._public(hook)

    def remove(self, hook_id):
        with self._lock:
            before = len(self._hooks)
            self._hooks = [h for h in self._hooks if h["id"] != hook_id]
            if len(self._hooks) == before:
                return False
            self._stats.pop(hook_id, None)
            self._save_locked()
            return True

    # -- stats --

    def note(self, hook_id, ok, status=None, error=None, dead_letter=False):
        with self._lock:
            s = self._stats.setdefault(hook_id, {
                "delivered": 0, "failed": 0, "last_status": None,
                "last_error": None, "last_attempt_at": None,
                "dead_letters": 0, "parked_until": None})
            if ok:
                s["delivered"] += 1
                s["dead_letters"] = 0
                s["parked_until"] = None
            else:
                s["failed"] += 1
                if dead_letter:
                    s["dead_letters"] = s.get("dead_letters", 0) + 1
                    if (config.webhook_park_s > 0 and
                            s["dead_letters"] >= config.webhook_park_after):
                        # park the URL (#100): a dead endpoint must not be
                        # retried forever — it cools down, then gets one
                        # real attempt again (and unparks on success)
                        s["parked_until"] = time.time() + config.webhook_park_s
                        log.warning("webhooks: hook %s parked for %.0fs "
                                    "after %d dead letter(s)",
                                    hook_id, config.webhook_park_s,
                                    s["dead_letters"])
                        METRICS.inc("tonearm_webhook_hooks_parked_total",
                                    help_text="Times a hook was parked after "
                                              "repeated dead letters")
            s["last_status"] = status
            s["last_error"] = None if ok else (error or "")[:300] or None
            s["last_attempt_at"] = time.time()


def _new_hook_id():
    return "wh_" + secrets.token_hex(6)


# ------------------------------------------------------------- delivery
# One worker, one time-ordered heap. Retries are re-inserted at their due
# time, so a slow receiver never blocks a healthy one.

class DeliveryWorker(threading.Thread):
    def __init__(self, registry, max_attempts=None, timeout=None,
                 backoff=DEFAULT_BACKOFF_S, clock=time.time,
                 send_fn=None, queue_max=2000):
        super().__init__(daemon=True, name="tonearm-webhooks")
        self.registry = registry
        self.max_attempts = max(1, max_attempts or config.webhook_attempts)
        self.timeout = timeout or config.webhook_timeout
        self.backoff = tuple(backoff)
        self._clock = clock
        self._send_fn = send_fn or self._post
        self._queue_max = queue_max
        self._heap = []
        self._seq = 0
        self._cv = threading.Condition()
        self._stop = threading.Event()
        self._recent = deque(maxlen=100)
        self._dropped = 0

    # -- public surface --

    def submit(self, event):
        """Fan one event out to matching hooks. Returns the queued count.
        Never blocks on HTTP and never raises."""
        try:
            hooks = self.registry.matching(event["type"])
        except Exception as e:                # a corrupt registry must not
            log.warning("webhooks: fan-out failed: %s", e)
            return 0
        if not hooks:
            return 0
        queued = 0
        with self._cv:
            for hook in hooks:
                if len(self._heap) >= self._queue_max:
                    # drop OLDEST (#99): the smallest due time is the most
                    # stale delivery; fresh events keep their place
                    heapq.heappop(self._heap)
                    self._dropped += 1
                    METRICS.inc("tonearm_webhook_deliveries_total",
                                {"result": "dropped"},
                                help_text="Webhook delivery attempts by result")
                self._seq += 1
                heapq.heappush(self._heap, (
                    self._clock(), self._seq,
                    {"event": event, "hook": hook, "attempt": 1,
                     "delivery_id": event["id"]}))
                queued += 1
            self._cv.notify()
        self._gauge()
        return queued

    def deliver_now(self, hook, event):
        """One synchronous attempt for the `test` endpoint. No retry: the
        caller wants the answer now, not a background retry later."""
        job = {"event": event, "hook": hook, "attempt": 1,
               "delivery_id": event["id"], "no_retry": True}
        return self._attempt(job)

    def pending(self):
        with self._cv:
            return len(self._heap)

    def recent(self, limit=50):
        with self._cv:
            return list(self._recent)[-max(1, min(limit, 100)):][::-1]

    def stop(self):
        self._stop.set()
        with self._cv:
            self._cv.notify()

    # -- worker loop --

    def run(self):
        log.info("webhook delivery worker armed (%d attempt max, %.0fs "
                 "timeout)", self.max_attempts, self.timeout)
        while not self._stop.is_set():
            job = None
            with self._cv:
                while not self._stop.is_set():
                    now = self._clock()
                    if self._heap and self._heap[0][0] <= now:
                        job = heapq.heappop(self._heap)[2]
                        break
                    wait = (self._heap[0][0] - now) if self._heap else None
                    self._cv.wait(wait)
                if self._stop.is_set():
                    break
            if job is not None:
                try:
                    self._attempt(job)
                except Exception as e:        # the worker must never die
                    log.error("webhooks: delivery crashed (kept alive): %s", e)
                self._gauge()

    def _gauge(self):
        with self._cv:
            METRICS.gauge("tonearm_webhook_pending", len(self._heap),
                          help_text="Webhook deliveries waiting to be sent "
                                    "(including retries)")
            METRICS.gauge("tonearm_webhook_dropped", self._dropped,
                          help_text="Webhook deliveries dropped because the "
                                    "pending queue was full")

    # -- one attempt --

    def _attempt(self, job):
        t0 = self._clock()
        status, error = self._send_fn(job["hook"], job["event"],
                                      job["attempt"], self.timeout)
        duration_ms = int((self._clock() - t0) * 1000)
        ok = status is not None and 200 <= status < 300
        result = {"ok": ok, "status": status, "error": error,
                  "duration_ms": duration_ms, "retry_scheduled": False,
                  "hook_id": job["hook"]["id"],
                  "event_id": job["event"]["id"],
                  "event": job["event"]["type"]}
        if not ok and not job.get("no_retry") and self._should_retry(status) \
                and job["attempt"] < self.max_attempts:
            job = dict(job, attempt=job["attempt"] + 1)
            delay = self.backoff[min(job["attempt"] - 2,
                                     len(self.backoff) - 1)]
            with self._cv:
                self._seq += 1
                heapq.heappush(self._heap, (self._clock() + delay, self._seq,
                                            job))
                self._cv.notify()
            result["retry_scheduled"] = True
            log.info("webhooks: %s -> %s failed (%s) — retry %d/%d in %ss",
                     job["event"]["type"], job["hook"]["url"],
                     error or status, job["attempt"], self.max_attempts, delay)
        elif not ok:
            log.warning("webhooks: %s -> %s dead-lettered after %d attempt(s) "
                        "(%s)", job["event"]["type"], job["hook"]["url"],
                        job["attempt"], error or status)
        # the registry learns the FINAL outcome: repeated dead letters park
        # the URL (#100); a success resets the streak and unparks
        self.registry.note(job["hook"]["id"], ok, status=status, error=error,
                           dead_letter=not ok and not result["retry_scheduled"])
        METRICS.inc("tonearm_webhook_deliveries_total",
                    {"result": "ok" if ok else "failed"},
                    help_text="Webhook delivery attempts by result")
        METRICS.observe("tonearm_webhook_delivery_duration_seconds",
                        max(0.0, duration_ms / 1000.0),
                        help_text="Webhook delivery attempt duration")
        self._remember(job, result)
        return result

    def _should_retry(self, status):
        return status is None or status in RETRYABLE_STATUS or status >= 500

    def _remember(self, job, result):
        with self._cv:
            self._recent.append({
                "event_id": result["event_id"], "event": result["event"],
                "hook_id": result["hook_id"], "url": job["hook"]["url"],
                "attempt": job["attempt"], "status": result["status"],
                "ok": result["ok"], "error": result["error"],
                "duration_ms": result["duration_ms"],
                "retry_scheduled": result["retry_scheduled"],
                "at": time.time()})

    def _post(self, hook, event, attempt, timeout):
        body = json.dumps(event, separators=(",", ":")).encode()
        headers = {"Content-Type": "application/json",
                   "User-Agent": f"tonearm/{__version__}",
                   "X-Tonearm-Event": event["type"],
                   "X-Tonearm-Delivery": event["id"],
                   "X-Tonearm-Attempt": str(attempt),
                   "X-Tonearm-Timestamp": str(int(time.time()))}
        secret = hook.get("secret")
        if secret:
            # signed over "<timestamp>.<body>" — receivers verify the hex AND
            # may enforce freshness on X-Tonearm-Timestamp (#103)
            headers["X-Tonearm-Signature"] = "sha256=" + sign(
                secret, body, ts=headers["X-Tonearm-Timestamp"])
        req = urllib.request.Request(hook["url"], data=body, method="POST",
                                     headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                r.read(1024)                  # drain; receivers may not care
                return r.status, None
        except urllib.error.HTTPError as e:
            return e.code, f"HTTP {e.code}"
        except Exception as e:                # network, DNS, timeout, TLS
            return None, str(e)[:300]


# ------------------------------------------------------------- producers
# The stream watcher rides the SAME event buffer the store and Last.fm
# drain (own cursor, zero new evals) and emits only on transitions.

def _renderer_available(browser_instance):
    """Same politeness rule as the store's writer: an ACTIVE stall skips the
    tick; a cold renderer (never connected) is allowed to trigger the first
    connect."""
    try:
        wd = browser_instance.health()
    except Exception:
        return False
    if wd.get("last_ok") is False or (wd.get("consecutive_failures") or 0) > 0:
        return False
    return True


class StreamWatcher(threading.Thread):
    CADENCE_S = 2.0

    def __init__(self, emit_fn, browser_instance, mk_mod, cadence_s=None):
        super().__init__(daemon=True, name="tonearm-webhooks-stream")
        self._emit = emit_fn
        self._browser = browser_instance
        self._mk = mk_mod
        self.cadence = cadence_s or self.CADENCE_S
        self._seq = 0
        self._current = None
        self._playing = None
        self._stop = threading.Event()

    def stop(self):
        self._stop.set()

    @staticmethod
    def _track(e):
        ts = e.get("ts")
        return {"id": e.get("id"), "title": e.get("title"),
                "artist": e.get("artist"), "album": e.get("album"),
                "duration_ms": e.get("durationMs"),
                "artwork": e.get("artworkUrl"),
                "started_at": round(ts / 1000.0, 3) if ts else None}

    def process_events(self, entries):
        """Pure transition -> event mapping (tests feed synthetic buffers).
        Progress ticks and same-track state churn emit nothing."""
        out = []
        for e in entries:
            self._seq = max(self._seq, e.get("seq", 0))
            key = e.get("id") or e.get("title")
            if not key:
                continue
            playing = e.get("isPlaying") is not False
            was = self._playing
            if playing:
                if key != self._current:
                    self._current = key
                    out.append((TRACK_CHANGE, self._track(e)))
                elif was is False:
                    out.append((PLAYBACK_RESUMED, self._track(e)))
            elif was is True:
                out.append((PLAYBACK_PAUSED, self._track(e)))
            self._playing = playing
        for event_type, data in out:
            try:
                self._emit(event_type, data)
            except Exception as e:            # emitting must never kill the
                log.warning("webhooks: emit failed: %s", e)  # watcher
        return out

    def run(self):
        log.info("webhook stream watcher armed (cadence %.0fs) — rides the "
                 "stream hook buffer, adds zero eval kinds", self.cadence)
        hooked = False
        while not self._stop.wait(self.cadence):
            if not _renderer_available(self._browser):
                continue
            if not hooked:
                try:
                    self._mk.install_stream_hook()
                    hooked = True
                except Exception as e:
                    log.debug("webhook hook install skipped: %s", e)
                    continue
            try:
                entries = self._mk.drain_stream(self._seq)
            except Exception as e:
                log.debug("webhook drain skipped: %s", e)
                continue
            if entries:
                self.process_events(entries)


# ------------------------------------------------------------- lifecycle
# Module-level singletons (routes and producers import `emit`; main.py owns
# start/stop). `emit` is a cheap no-op until start() has armed the worker.

_registry = None
_worker = None
_watcher = None


def start():
    """Arm the registry, delivery worker and stream watcher. Opt-in only:
    TONEARM_WEBHOOKS=1. Never raises — a bad config must not stop the API."""
    global _registry, _worker, _watcher
    if not config.webhooks_enabled or _worker is not None:
        return
    _registry = WebhookRegistry(config.webhooks_config_path()).load()
    _worker = DeliveryWorker(_registry)
    _worker.start()
    try:
        from .browser import browser
        from . import musickit as mk
        _watcher = StreamWatcher(emit, browser, mk)
        _watcher.start()
    except Exception as e:
        log.error("webhook stream watcher failed to start: %s", e)
    log.info("webhooks armed: %d hook(s), config %s",
             _registry.count(), _registry.path)


def stop():
    global _registry, _worker, _watcher
    for t in (_watcher, _worker):
        if t is not None:
            try:
                t.stop()
            except Exception:
                pass
    for t in (_watcher, _worker):
        if t is not None:
            try:
                t.join(timeout=2)
            except Exception:
                pass
    _watcher = None
    _worker = None
    _registry = None


def emit(event_type, data=None):
    """Publish one event. Safe to call from any thread, any time: a no-op
    when the feature is off or the worker has stopped."""
    worker = _worker
    if worker is None:
        return
    event = make_event(event_type, data)
    METRICS.inc("tonearm_webhook_events_total", {"type": event_type},
                help_text="Webhook events emitted by type")
    try:
        worker.submit(event)
    except Exception as e:
        log.warning("webhooks: submit failed: %s", e)


def snapshot():
    """Management view: hooks (secrets redacted) + pending + recent stats.
    Raises WebhooksDisabled so the route can answer an honest 501."""
    if not config.webhooks_enabled:
        raise WebhooksDisabled(
            "outbound webhooks are disabled — set TONEARM_WEBHOOKS=1 "
            "(hooks are stored on your volume, nothing leaves it until then)")
    registry = _registry
    worker = _worker
    if registry is None:
        # enabled but not started yet (e.g. import-time call in a test)
        registry = WebhookRegistry(config.webhooks_config_path()).load()
    return {"enabled": True,
            "hooks": registry.public_hooks(),
            "pending": worker.pending() if worker is not None else 0,
            "recent": worker.recent(25) if worker is not None else [],
            "note": "delivery is at-least-once; pending deliveries are "
                    "in-memory and are lost on restart"}


def deliveries(limit=50):
    if not config.webhooks_enabled:
        raise WebhooksDisabled("outbound webhooks are disabled — set "
                               "TONEARM_WEBHOOKS=1")
    worker = _worker
    return {"count": 0 if worker is None else len(worker.recent(limit)),
            "items": [] if worker is None else worker.recent(limit)}


def add_hook(url, events=None, secret=None, enabled=True):
    registry = _require_registry()
    return registry.add(url, events=events, secret=secret, enabled=enabled)


def update_hook(hook_id, **fields):
    return _require_registry().update(hook_id, **fields)


def remove_hook(hook_id):
    return _require_registry().remove(hook_id)


def test_hook(hook_id):
    """Synchronously deliver a `webhook.test` event to one hook."""
    registry = _require_registry()
    hook = registry.get(hook_id)
    if hook is None:
        return None
    event = make_event(WEBHOOK_TEST, {"hook_id": hook_id,
                                      "message": "tonearm test delivery"})
    worker = _worker
    if worker is None:
        return {"ok": False, "status": None,
                "error": "delivery worker is not running", "duration_ms": 0}
    return worker.deliver_now(hook, event)


def _require_registry():
    if not config.webhooks_enabled:
        raise WebhooksDisabled("outbound webhooks are disabled — set "
                               "TONEARM_WEBHOOKS=1")
    global _registry
    if _registry is None:
        _registry = WebhookRegistry(config.webhooks_config_path()).load()
    return _registry
