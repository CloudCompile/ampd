"""Local persistence — the v0.3 "Memory" phase. sqlite3 stdlib, WAL.

Design constraints (the hard-won kind, encoded):

* OFF by default. Every store-backed surface answers 501 with an honest
  hint when AMPD_STORE is unset — opt-in surfaces must never fake it.
* ONE flat lock around the connection (created with check_same_thread=
  False). No nested locking, no re-entrant cleverness — the same discipline
  that keeps the CDP layer alive.
* The history writer adds ZERO new eval kinds: it consumes the same
  stream-hook buffer the SSE listeners drain (window.__ampdBuf), on a slow
  cadence, and skips ticks entirely while the watchdog reports a stall.
  Persistence must never compete with the renderer it is recording.
* Plays dedupe on (track_id, started_at) — a restart, an overlapping drain,
  or a replayed hook event must never double-write a play.
* Library rows are keyed by LIBRARY id (i.xxx): fresh rows often lack a
  catalog id, and removals are keyed in this space. `catalog_id` is kept
  when known but is never the identity.

Schema (versioned via _meta.schema_version; migrate chain below):
  _meta(key TEXT PRIMARY KEY, value TEXT)
  plays(id INTEGER PRIMARY KEY AUTOINCREMENT,
        track_id TEXT NOT NULL, title TEXT, artist TEXT, album TEXT,
        artwork TEXT, duration_ms INTEGER, started_at REAL NOT NULL,
        UNIQUE(track_id, started_at))
  library(library_id TEXT PRIMARY KEY, catalog_id TEXT, name TEXT,
          artist TEXT, album TEXT, duration_ms INTEGER, kind TEXT,
          attributes TEXT,               -- raw Apple attributes JSON
          first_seen REAL, last_seen REAL, last_changed REAL)
  cursors(name TEXT PRIMARY KEY, value TEXT, updated_at REAL)

The `library` table holds the CURRENT known state with watermarks
(first_seen / last_seen / last_changed), updated by the periodic snapshot
walk. Diffing "the two newest snapshots" (ROADMAP wording) is computed from
the watermarks: added = first_seen > since; updated = last_changed > since
and not added; removed = last_seen <= since. One table, no snapshot forks.
"""
import json
import logging
import os
import sqlite3
import threading
import time

from .config import config
from .metrics import METRICS

log = logging.getLogger("ampd.store")

SCHEMA_VERSION = 1

_MIGRATIONS = {
    1: """
    CREATE TABLE IF NOT EXISTS _meta (
        key TEXT PRIMARY KEY, value TEXT);
    CREATE TABLE IF NOT EXISTS plays (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        track_id TEXT NOT NULL,
        title TEXT, artist TEXT, album TEXT, artwork TEXT,
        duration_ms INTEGER,
        started_at REAL NOT NULL,
        UNIQUE(track_id, started_at));
    CREATE INDEX IF NOT EXISTS idx_plays_started ON plays(started_at);
    CREATE TABLE IF NOT EXISTS scrobbles (
        track_id TEXT NOT NULL,
        started_at REAL NOT NULL,
        scrobbled_at REAL NOT NULL,
        UNIQUE(track_id, started_at));
    CREATE TABLE IF NOT EXISTS library (
        library_id TEXT PRIMARY KEY,
        catalog_id TEXT, name TEXT, artist TEXT, album TEXT,
        duration_ms INTEGER, kind TEXT, attributes TEXT,
        first_seen REAL, last_seen REAL, last_changed REAL);
    CREATE INDEX IF NOT EXISTS idx_library_last_seen ON library(last_seen);
    CREATE TABLE IF NOT EXISTS cursors (
        name TEXT PRIMARY KEY, value TEXT, updated_at REAL);
    """,
}


class Store:
    """sqlite-backed local state. All methods no-op safely when disabled
    (and read methods raise StoreDisabled so routes can 501 honestly)."""

    def __init__(self, path=None, enabled=None):
        self.enabled = config.store_enabled if enabled is None else enabled
        self.path = path or config.store_db_path()
        self._conn = None
        self._lock = threading.Lock()

    # ------------------------------------------------------------- lifecycle

    def start(self):
        """Open the db (creating it if needed) and arm the history writer."""
        if not self.enabled:
            return
        with self._lock:
            if self._conn is not None:
                return
            d = os.path.dirname(self.path)
            if d:
                os.makedirs(d, exist_ok=True)
                try:                       # the db dir holds private history
                    os.chmod(d, 0o700)
                except OSError:
                    pass
            self._conn = sqlite3.connect(self.path, check_same_thread=False,
                                         timeout=30)
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA busy_timeout=10000")
            self._conn.execute("PRAGMA synchronous=NORMAL")
            self._migrate()
        log.info("store open at %s", self.path)

    def _migrate(self):
        has_meta = self._conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='_meta'"
        ).fetchone() is not None
        current = 0
        if has_meta:
            cur = self._conn.execute(
                "SELECT value FROM _meta WHERE key='schema_version'").fetchone()
            current = int(cur[0]) if cur else 0
        for version in sorted(_MIGRATIONS):
            if version > current:
                self._conn.executescript(_MIGRATIONS[version])
                self._conn.execute(
                    "INSERT INTO _meta(key, value) VALUES('schema_version', ?) "
                    "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                    (str(version),))
                self._conn.commit()
                log.info("store schema migrated to v%d", version)

    def close(self):
        with self._lock:
            if self._conn is not None:
                try:
                    self._conn.commit()
                    self._conn.close()
                except Exception:
                    pass
                self._conn = None

    def _require_conn(self):
        if not self.enabled or self._conn is None:
            raise StoreDisabled(
                "the local store is disabled — set AMPD_STORE=1 "
                "(data lives only on your volume either way)")
        return self._conn

    # ------------------------------------------------------------- plays

    def record_play(self, track_id, title, artist, album, artwork,
                    duration_ms, started_at):
        """One play. Idempotent on (track_id, started_at) — INSERT OR IGNORE."""
        conn = self._require_conn()
        with self._lock:
            conn.execute(
                "INSERT OR IGNORE INTO plays(track_id, title, artist, album, "
                "artwork, duration_ms, started_at) VALUES(?,?,?,?,?,?,?)",
                (track_id, title, artist, album, artwork, duration_ms,
                 started_at))
            conn.commit()
        METRICS.inc("ampd_store_plays_written_total",
                    help_text="play rows persisted (dedupes included)")

    def record_scrobble(self, track_id, started_at):
        """Mark a play as scrobbled. Returns False if it was ALREADY
        recorded — the dedupe that makes restarts never double-scrobble
        (#98): the marker is UNIQUE(track_id, started_at), same key as the
        play itself."""
        conn = self._require_conn()
        with self._lock:
            cur = conn.execute(
                "INSERT OR IGNORE INTO scrobbles(track_id, started_at, "
                "scrobbled_at) VALUES(?,?,?)",
                (track_id, started_at, time.time()))
            conn.commit()
            return cur.rowcount > 0

    def recently_played(self, limit=50, offset=0):
        """The archive: newest first, past Apple's ~20-item cap."""
        conn = self._require_conn()
        with self._lock:
            rows = conn.execute(
                "SELECT track_id, title, artist, album, artwork, duration_ms, "
                "started_at FROM plays ORDER BY started_at DESC, id DESC "
                "LIMIT ? OFFSET ?", (min(limit, 500), max(offset, 0))).fetchall()
            total = conn.execute("SELECT COUNT(*) FROM plays").fetchone()[0]
        items = [{"id": r[0], "title": r[1], "artist": r[2], "album": r[3],
                  "artwork": r[4], "duration_ms": r[5],
                  "played_at": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                             time.gmtime(r[6]))}
                 for r in rows]
        nxt = offset + len(rows)
        return {"total": total, "count": len(items),
                "items": items,
                "next_offset": nxt if nxt < total and items else None}

    # ------------------------------------------------------------- library

    def upsert_library_rows(self, rows):
        """Upsert a snapshot walk batch. `rows` are normalized item dicts
        (mk.item_row shape). Identity = library_id. first_seen set once;
        last_seen bumped every walk; last_changed only on real change."""
        conn = self._require_conn()
        now = time.time()
        with self._lock:
            for r in rows:
                lid = r.get("library_id") or r.get("id")
                if not lid:
                    continue
                attrs = json.dumps(r.get("attributes") or {}, separators=(",", ":"))
                cur = conn.execute(
                    "SELECT name, artist, album, catalog_id, duration_ms, "
                    "attributes, first_seen FROM library WHERE library_id=?",
                    (lid,)).fetchone()
                if cur is None:
                    conn.execute(
                        "INSERT INTO library(library_id, catalog_id, name, "
                        "artist, album, duration_ms, kind, attributes, "
                        "first_seen, last_seen, last_changed) "
                        "VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                        (lid, r.get("catalog_id"), r.get("name"), r.get("artist"),
                         r.get("album"), r.get("duration_ms"),
                         r.get("type") or r.get("kind"), attrs, now, now, now))
                    continue
                (old_name, old_artist, old_album, old_cat, old_dur,
                 old_attrs, first_seen) = cur
                changed = (old_name != r.get("name") or
                           old_artist != r.get("artist") or
                           old_album != r.get("album") or
                           old_attrs != attrs or
                           (old_cat or None) != (r.get("catalog_id") or None) or
                           old_dur != r.get("duration_ms"))
                conn.execute(
                    "UPDATE library SET catalog_id=?, name=?, artist=?, "
                    "album=?, duration_ms=?, kind=?, attributes=?, "
                    "last_seen=?, last_changed=? WHERE library_id=?",
                    (r.get("catalog_id"), r.get("name"), r.get("artist"),
                     r.get("album"), r.get("duration_ms"),
                     r.get("type") or r.get("kind"), attrs,
                     now, now if changed else first_seen, lid))
            conn.commit()

    def library_rows(self, limit=100000, offset=0):
        conn = self._require_conn()
        with self._lock:
            rows = conn.execute(
                "SELECT library_id, catalog_id, name, artist, album, "
                "duration_ms, kind, attributes, first_seen, last_seen, "
                "last_changed FROM library ORDER BY name LIMIT ? OFFSET ?",
                (limit, offset)).fetchall()
        out = []
        for r in rows:
            out.append({
                "library_id": r[0], "catalog_id": r[1], "name": r[2],
                "artist": r[3], "album": r[4], "duration_ms": r[5],
                "kind": r[6],
                "attributes": json.loads(r[7]) if r[7] else {},
                "first_seen": r[8], "last_seen": r[9], "last_changed": r[10],
            })
        return out

    def library_count(self):
        conn = self._require_conn()
        with self._lock:
            return conn.execute("SELECT COUNT(*) FROM library").fetchone()[0]

    # ---- diff queries (watermark-driven; see module docstring) ----

    def _rows_where(self, where, args, limit, offset):
        conn = self._require_conn()
        with self._lock:
            rows = conn.execute(
                f"SELECT library_id, catalog_id, name, artist, album, "
                f"duration_ms, kind, first_seen, last_seen, last_changed "
                f"FROM library WHERE {where} ORDER BY last_changed DESC, "
                f"library_id LIMIT ? OFFSET ?", (*args, limit, offset)).fetchall()
            total = conn.execute(
                f"SELECT COUNT(*) FROM library WHERE {where}", args).fetchone()[0]
        out = [{"library_id": r[0], "catalog_id": r[1], "name": r[2],
                "artist": r[3], "album": r[4], "duration_ms": r[5],
                "kind": r[6], "first_seen": r[7], "last_seen": r[8],
                "last_changed": r[9]} for r in rows]
        nxt = offset + len(out)
        return {"total": total, "count": len(out), "items": out,
                "next_offset": nxt if nxt < total and out else None}

    def library_added_since(self, since, limit=100, offset=0):
        """Rows first seen after `since`. since=0 -> the whole library."""
        return self._rows_where("first_seen > ?", (since,), limit, offset)

    def library_updated_since(self, since, limit=100, offset=0):
        """Rows that CHANGED after `since` (not counting brand-new ones)."""
        return self._rows_where("last_changed > ? AND first_seen <= ?",
                                (since, since), limit, offset)

    def library_removed_since(self, since, limit=100, offset=0):
        """Rows whose most recent walk predates `since` — gone from the
        library as of the last completed snapshot walk."""
        return self._rows_where("last_seen <= ?", (since,), limit, offset)

    # ------------------------------------------------------------- stats
    # Pure local computation — no Apple calls. Aggregation in SQL, never
    # Python loops over the whole table. Plays dedupe on (track_id,
    # started_at) is the writer's guarantee; stats just read.

    def stats(self, since=0.0, limit=25):
        conn = self._require_conn()
        with self._lock:
            tracks = conn.execute(
                "SELECT track_id, title, artist, COUNT(*) AS plays "
                "FROM plays WHERE started_at >= ? GROUP BY track_id "
                "ORDER BY plays DESC, MAX(started_at) DESC LIMIT ?",
                (since, limit)).fetchall()
            artists = conn.execute(
                "SELECT artist, COUNT(*) AS plays FROM plays "
                "WHERE started_at >= ? AND artist IS NOT NULL "
                "GROUP BY artist ORDER BY plays DESC LIMIT ?",
                (since, limit)).fetchall()
            total = conn.execute(
                "SELECT COUNT(*) FROM plays WHERE started_at >= ?",
                (since,)).fetchone()[0]
        return {"window_since": since,
                "total_plays": total,
                "top_tracks": [{"id": r[0], "title": r[1], "artist": r[2],
                                "plays": r[3]} for r in tracks],
                "top_artists": [{"artist": r[0], "plays": r[1]}
                                for r in artists]}

    def plays_series(self, since=0.0):
        """Plays per UTC day — bucketed in SQL for charts."""
        conn = self._require_conn()
        with self._lock:
            rows = conn.execute(
                "SELECT date(started_at, 'unixepoch') AS day, COUNT(*) "
                "FROM plays WHERE started_at >= ? GROUP BY day ORDER BY day",
                (since,)).fetchall()
        return [{"day": r[0], "plays": r[1]} for r in rows]

    # ------------------------------------------------------------- cursors

    def set_cursor(self, name, value):
        conn = self._require_conn()
        with self._lock:
            conn.execute(
                "INSERT INTO cursors(name, value, updated_at) VALUES(?,?,?) "
                "ON CONFLICT(name) DO UPDATE SET value=excluded.value, "
                "updated_at=excluded.updated_at",
                (name, json.dumps(value), time.time()))
            conn.commit()

    def get_cursor(self, name, default=None):
        conn = self._require_conn()
        with self._lock:
            row = conn.execute(
                "SELECT value FROM cursors WHERE name=?", (name,)).fetchone()
        if not row:
            return default
        try:
            return json.loads(row[0])
        except (json.JSONDecodeError, TypeError):
            return default


class StoreDisabled(RuntimeError):
    """Raised by store read methods when the store is off; routes map it to
    an honest 501."""


# --------------------------------------------------------------- diff (pure)

def diff_rows(rows_before, rows_after, before_ts, after_ts):
    """Pure diff between two row lists (mk.item_row-normalized). Identity is
    library_id; rows without one match by (name, artist, album) as a display
    hint only. Returns {'added': [...], 'updated': [...], 'removed': [...]}.
    Timestamps come from the store watermarks, not wall clocks, so a diff
    never lies about when a change landed."""
    def key(r):
        return r.get("library_id") or r.get("id")

    def name_key(r):
        return ((r.get("name") or "").lower(),
                (r.get("artist") or "").lower(),
                (r.get("album") or "").lower())

    before = {key(r): r for r in rows_before if key(r)}
    after = {key(r): r for r in rows_after if key(r)}

    added = [after[k] for k in after
             if k not in before and
             (after[k].get("first_seen") or 0) > before_ts]
    updated = [after[k] for k in after if k in before and
               (after[k].get("last_changed") or 0) > before_ts and
               after[k] not in added]
    removed = [before[k] for k in before if k not in after and
               (before[k].get("last_seen") or 0) <= after_ts]
    # sort each by watermark, newest first, for stable, readable output
    for lst, field in ((added, "first_seen"), (updated, "last_changed"),
                       (removed, "last_seen")):
        lst.sort(key=lambda r: r.get(field) or 0, reverse=True)
    return {"added": added, "updated": updated, "removed": removed,
            "since": before_ts, "until": after_ts}


def _renderer_available(browser_instance):
    """False only on an ACTIVE stall (failed pings / failing renderer).
    A COLD renderer (never connected — last_ping_ts is None) counts as
    available: background work must be able to trigger the first connect,
    or every thread would politely defer to the watchdog while the watchdog
    waits for a first connect — a deadlock of politeness where the archive
    never starts."""
    try:
        wd = browser_instance.health()
    except Exception:
        return False
    if wd.get("last_ok") is False or (wd.get("consecutive_failures") or 0) > 0:
        return False
    return True


# ---------------------------------------------------------------- history
# the history writer: ONE flat daemon thread, drains the stream-hook buffer
# the SSE listeners already use, persists track starts. Skips ticks when the
# watchdog reports a stall (persistence must never kick a limping renderer).

class HistoryWriter(threading.Thread):
    CADENCE_S = 5.0

    def __init__(self, store, browser_instance, mk_mod, cadence_s=None):
        super().__init__(daemon=True, name="ampd-store-history")
        self.store = store
        self._browser = browser_instance
        self._mk = mk_mod
        self.cadence = cadence_s or self.CADENCE_S
        self._seq = 0
        self._current = None          # last seen track key
        self._playing = None          # last seen is-playing state
        self._stop = threading.Event()

    def stop(self):
        self._stop.set()

    def _stalled(self):
        return not _renderer_available(self._browser)

    def process_events(self, entries):
        """Pure event -> play rows. Split from the loop so tests can feed it
        synthetic buffers without any renderer.
        A 'play' = the track key changes while playing (progress ticks and
        same-track state changes are not plays), or playback resumes from a
        pause. The very first track seen playing counts too — a server
        restart mid-song still happened."""
        recorded = []
        for e in entries:
            self._seq = max(self._seq, e.get("seq", 0))
            key = e.get("id") or e.get("title")
            if not key:
                continue
            playing = e.get("isPlaying") is not False
            was_playing = self._playing
            if playing and (key != self._current or was_playing is False):
                self._current = key
                self._playing = True
                started_at = (e.get("ts") or time.time() * 1000) / 1000.0
                self.store.record_play(
                    track_id=key, title=e.get("title"), artist=e.get("artist"),
                    album=e.get("album"), artwork=e.get("artworkUrl"),
                    duration_ms=e.get("durationMs"), started_at=started_at)
                recorded.append(key)
            elif not playing:
                self._playing = False
        return recorded

    def run(self):
        log.info("history writer armed (cadence %.0fs) — rides the stream "
                 "hook buffer, adds zero eval kinds", self.cadence)
        hooked = False
        while not self._stop.wait(self.cadence):
            if not self.store.enabled:
                continue
            if self._stalled():
                continue
            if not hooked:
                # one-shot: the hook exists only once an SSE client connected
                # (or we install it now). Idempotent JS — checks __ampdHooked.
                try:
                    self._mk.install_stream_hook()
                    hooked = True
                except Exception as e:
                    log.debug("hook install skipped: %s", e)
                    continue
            try:
                entries = self._mk.drain_stream(self._seq)
            except Exception as e:
                log.debug("history drain skipped: %s", e)
                continue
            if not entries:
                continue
            try:
                got = self.process_events(entries)
                if got:
                    log.debug("history: %d play(s) persisted", len(got))
            except Exception as e:
                log.warning("history write failed (kept alive): %s", e)


# ------------------------------------------------------------- snapshots
# the periodic library walk: ONE bounded thread, single-flight (never overlaps
# itself), stall-gated (a full walk is ~1 eval per 100 songs — it must never
# fight a limping renderer for the eval lock). Records its runs in cursors.

class SnapshotScheduler(threading.Thread):
    """Periodically walks /v1/me/library/songs and upserts the store.
    `walk_fn` is injected so tests can drive it without any renderer."""

    def __init__(self, store, browser_instance, mk_mod, interval=None,
                 walk_fn=None):
        super().__init__(daemon=True, name="ampd-store-snapshot")
        self.store = store
        self._browser = browser_instance
        self._mk = mk_mod
        self.interval = interval or config.store_sync_interval
        self._walk_fn = walk_fn or self._walk_library
        self._busy = threading.Lock()      # single-flight: walk never overlaps
        self._stop = threading.Event()

    def stop(self):
        self._stop.set()

    def _stalled(self):
        return not _renderer_available(self._browser)

    def _walk_library(self):
        """The real walk: every library song, normalized rows, in batches.
        ~1 eval per 100 songs (Apple's page cap)."""
        def extract(data):
            return [self._mk.item_row(t) for t in data.get("data", [])]
        return self._mk.paginated("/v1/me/library/songs?limit=100", extract,
                                  fresh=True)

    def run_walk(self):
        """One complete walk. Returns a summary dict; safe to call directly
        (the thread calls this too)."""
        if not self._busy.acquire(timeout=0.1):
            return {"ran": False, "reason": "previous walk still running"}
        try:
            t0 = time.time()
            rows = self._walk_fn()
            # upsert in batches so one giant commit never pins the lock
            BATCH = 500
            for i in range(0, len(rows), BATCH):
                self.store.upsert_library_rows(rows[i:i + BATCH])
            summary = {"ran": True,
                       "rows": len(rows),
                       "seconds": round(time.time() - t0, 1)}
            self.store.set_cursor("library.walk", summary)
            METRICS.inc("ampd_store_library_walks_total",
                        help_text="completed library snapshot walks")
            METRICS.gauge("ampd_store_library_rows", len(rows),
                          help_text="library rows in the last completed walk")
            return summary
        finally:
            self._busy.release()

    def run(self):
        log.info("snapshot scheduler armed: full library walk every %ds "
                 "(stall-gated, single-flight)", self.interval)
        # first run shortly after boot (renderer still fresh), then on cadence
        waited = 0.0
        while waited < 90 and not self._stop.wait(5):
            waited += 5
        while not self._stop.is_set():
            if self.store.enabled and not self._stalled():
                try:
                    summary = self.run_walk()
                    if summary.get("ran"):
                        log.info("library walk: %d rows in %.1fs",
                                 summary["rows"], summary["seconds"])
                except Exception as e:
                    log.warning("library walk failed (kept alive): %s", e)
            # park in 5s slices so stop() stays responsive
            slept = 0.0
            while slept < self.interval and not self._stop.is_set():
                self._stop.wait(min(5, self.interval - slept))
                slept += 5


# module-level singleton (routes import this; main.py owns its lifecycle)
store = Store()
history_writer: HistoryWriter | None = None   # set by main.py lifespan
snapshot_scheduler: SnapshotScheduler | None = None
export_scheduler = None   # ampd/exporter.ExportScheduler (set in main.py)
