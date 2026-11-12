"""Scheduled sweep digests (v0.6 Automation) — opt-in.

The sweeps in `/api/write/sweeps/*` are useful on demand; a digest makes
them ambient. One flat daemon thread runs a dry-run dedupe + never-played
report on a cadence and emits it as a `sweep.digest` webhook event.

Rules (same discipline as every other background walk):

* OFF by default (`TONEARM_DIGEST_INTERVAL=0`), and requires
  `TONEARM_WEBHOOKS=1` — a digest with nowhere to go is just wasted evals.
* **Stall-gated and single-flight**: a full walk must never fight a limping
  renderer, and two walks must never overlap.
* **One walk, two reports** (`tonearm/sweeps.py` builds both from the same
  rows) — the digest never doubles the library read cost.
* Never raises: a bad walk logs and waits for the next cadence.
"""
import logging
import threading

from .config import config

log = logging.getLogger("tonearm.digest")

FIRST_RUN_DELAY_S = 60       # let the renderer come up before the first walk


class DigestScheduler(threading.Thread):
    def __init__(self, browser_instance, interval=None, build_fn=None,
                 emit_fn=None):
        super().__init__(daemon=True, name="tonearm-digest")
        self._browser = browser_instance
        self.interval = interval or config.digest_interval
        self._build = build_fn
        self._emit = emit_fn
        self._stop = threading.Event()

    def stop(self):
        self._stop.set()

    def _stalled(self):
        try:
            wd = self._browser.health()
        except Exception:
            return True
        if wd.get("last_ok") is False or (wd.get("consecutive_failures") or 0) > 0:
            return True
        return False

    def run_once(self):
        """Build and emit one digest. Safe to call directly (tests do)."""
        from . import sweeps, webhooks
        build = self._build or sweeps.build_digest
        emit = self._emit or webhooks.emit
        payload = build()
        emit(webhooks.SWEEP_DIGEST, payload)
        return payload

    def run(self):
        log.info("digest scheduler armed: dry-run sweep every %ds "
                 "(stall-gated, single walk)", self.interval)
        waited = 0.0
        while waited < FIRST_RUN_DELAY_S and not self._stop.wait(5):
            waited += 5
        while not self._stop.is_set():
            if not self._stalled():
                try:
                    payload = self.run_once()
                    log.info("digest: %d songs, %d duplicate group(s), "
                             "%d never played",
                             payload.get("library_size", 0),
                             payload.get("duplicate_groups", 0),
                             payload.get("never_played", 0))
                except Exception as e:
                    log.warning("digest failed (kept alive): %s", e)
            slept = 0.0
            while slept < self.interval and not self._stop.is_set():
                self._stop.wait(min(5, self.interval - slept))
                slept += 5


# module-level singleton (set by main.py lifespan; tests may inspect it)
scheduler = None
