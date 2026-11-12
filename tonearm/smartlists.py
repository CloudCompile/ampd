"""Smart-playlist engine (v0.6 #44, #110, #111) — rules in, live playlist out.

The contract the ROADMAP promised:

* **Evaluation is LOCAL-ONLY.** Rules ("added after X, artist in Y, not
  played since Z") run against the local store's `library` rows and play
  history — zero Apple calls, zero evals. Apple is touched only at
  MATERIALIZATION: one find-or-create playlist, one full-list PUT
  (`mk.playlist_set_tracks`, library-songs ids — the same call reorder
  uses, so the playlist is exactly the evaluation, in order, last write
  wins).
* **Materialization is writes-gated** (TONEARM_ENABLE_WRITES=1) and
  **throttled**: a full-list PUT rebuilds the playlist on Apple's side,
  so each list carries a refresh floor (`TONEARM_SMARTLIST_MIN_REFRESH`).
* The scheduler is OFF by default (`TONEARM_SMARTLIST_INTERVAL=0`) —
  manual `POST /api/smartlists/{id}/refresh` for on-demand, the thread
  for ambient. Stall-gated like every background thread.

The rule dialect (#110) — JSON, all rules ANDed:
    {"field": ..., "op": ..., "value": ...}
  title / artist / album : contains | equals | starts | ends   (ci)
  genre                  : contains                             (ci, any of)
  play_count             : eq | gt | gte | lt | lte             (int)
  release_date           : after | before                       (ISO date)
  added                  : after | before   (store first_seen; ISO or epoch)
  last_played            : within_days | older_than_days | never
(last_played joins the plays archive on BOTH id spaces — the stream hook's
track id is the catalog id, the store's is the library id.)
"""
import logging
import threading
import time
import uuid

from .config import config

log = logging.getLogger("tonearm.smartlists")

STRING_OPS = ("contains", "equals", "starts", "ends")
NUM_OPS = ("eq", "gt", "gte", "lt", "lte")
DATE_OPS = ("after", "before")
LASTPLAYED_OPS = ("within_days", "older_than_days", "never")
FIELDS = {
    "title": STRING_OPS, "artist": STRING_OPS, "album": STRING_OPS,
    "genre": ("contains",),
    "play_count": NUM_OPS,
    "release_date": DATE_OPS, "added": DATE_OPS,
    "last_played": LASTPLAYED_OPS,
}
SORTS = ("added_desc", "added_asc", "name", "artist", "play_count_desc",
         "release_date_desc")


class SmartlistError(ValueError):
    """A bad rule/definition — routes map this to a 400."""


# ------------------------------------------------------------- validation

def validate_rules(rules):
    """Normalize + validate. Returns the rules as a clean list; raises
    SmartlistError on anything unknown (400, not a silent no-match)."""
    if rules is None:
        rules = []
    if not isinstance(rules, list):
        raise SmartlistError("rules must be a list of {field, op, value}")
    out = []
    for r in rules:
        if not isinstance(r, dict):
            raise SmartlistError(f"rule must be an object, got {type(r).__name__}")
        field, op = r.get("field"), r.get("op")
        if field not in FIELDS:
            raise SmartlistError(
                f"unknown rule field {field!r} — known: {sorted(FIELDS)}")
        if op not in FIELDS[field]:
            raise SmartlistError(
                f"field {field!r} accepts ops {sorted(FIELDS[field])}, "
                f"not {op!r}")
        if op != "never" and "value" not in r:
            raise SmartlistError(f"rule {field} {op} needs a value")
        out.append({"field": field, "op": op, "value": r.get("value")})
    return out


def validate_sort(sort):
    if sort not in SORTS:
        raise SmartlistError(f"sort must be one of {sorted(SORTS)}, "
                             f"not {sort!r}")
    return sort


def _parse_when(v):
    """'after/before' value: ISO date ('2026-01-31', compares as the day's
    end), ISO datetime, or epoch seconds. Returns epoch float."""
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v)
    try:
        return float(s)
    except ValueError:
        pass
    try:
        t = time.strptime(s[:10], "%Y-%m-%d")
        base = time.mktime(t)
    except ValueError as e:
        raise SmartlistError(f"date values must be YYYY-MM-DD or epoch "
                             f"seconds, got {v!r}") from e
    if "T" not in s and len(s) <= 10:
        return base + 86399          # the whole day, inclusive
    import calendar
    try:
        t2 = time.strptime(s[:19], "%Y-%m-%dT%H:%M:%S")
        return calendar.timegm(t2)   # ISO datetimes are UTC in the API
    except ValueError:
        return base + 86399


# ------------------------------------------------------------- evaluation
# Pure functions over store rows — no Apple, no threads, fully testable.

def _row_play_count(row):
    v = (row.get("attributes") or {}).get("playCount")
    return int(v) if isinstance(v, (int, float)) else None


def _rule_matches(row, rule, last_played, now):
    f, op, v = rule["field"], rule["op"], rule.get("value")
    if f == "last_played":
        # joined on BOTH id spaces (stream-hook ids are catalog ids)
        ts = None
        for key in (row.get("library_id"), row.get("catalog_id")):
            if key and key in last_played:
                ts = max(ts or 0, last_played[key])
        if op == "never":
            return ts is None
        if op == "within_days":
            return ts is not None and now - ts <= float(v) * 86400
        # older_than_days: "not played in N days" — a never-played track
        # satisfies it vacuously (AND it with play_count rules to exclude)
        return ts is None or now - ts > float(v) * 86400
    if f == "play_count":
        pc = _row_play_count(row)
        if pc is None:
            return False            # absent data never satisfies a count rule
        n = int(v)
        return {"eq": pc == n, "gt": pc > n, "gte": pc >= n,
                "lt": pc < n, "lte": pc <= n}[op]
    if f == "genre":
        genres = [(g or "").casefold()
                  for g in (row.get("attributes") or {}).get("genreNames", [])
                  if isinstance(g, str)] or \
                 [g.casefold() for g in (row.get("genres") or [])
                  if isinstance(g, str)]
        return str(v).casefold() in genres
    if f in ("release_date", "added"):
        when = _parse_when(v)
        if f == "added":
            rowv = row.get("first_seen") or 0
            return rowv > when if op == "after" else rowv <= when
        rd = (row.get("attributes") or {}).get("releaseDate") or ""
        if not rd:
            return False
        return rd[:10] > str(v)[:10] if op == "after" else rd[:10] <= str(v)[:10]
    # string fields ("title" is the rule's word for the row's "name")
    s = ((row.get("name") if f == "title" else row.get(f)) or "")
    q = str(v).casefold()
    s = s.casefold()
    return {"contains": q in s, "equals": s == q,
            "starts": s.startswith(q), "ends": s.endswith(q)}[op]


def evaluate(rows, rules, last_played=None, now=None):
    """Filter + sort + limit. `last_played` maps track id -> last epoch.
    Returns matched rows (store row dicts)."""
    rules = validate_rules(rules)
    now = now or time.time()
    last_played = last_played or {}
    out = [r for r in rows
           if all(_rule_matches(r, rule, last_played, now) for rule in rules)]
    return out


def sort_rows(rows, sort):
    sort = sort or "added_desc"
    if sort == "added_asc":
        return sorted(rows, key=lambda r: r.get("first_seen") or 0)
    if sort == "name":
        return sorted(rows, key=lambda r: (r.get("name") or "").casefold())
    if sort == "artist":
        return sorted(rows, key=lambda r: ((r.get("artist") or "").casefold(),
                                           (r.get("album") or "").casefold(),
                                           (r.get("name") or "").casefold()))
    if sort == "play_count_desc":
        return sorted(rows, key=lambda r: _row_play_count(r) or 0, reverse=True)
    if sort == "release_date_desc":
        return sorted(rows,
                      key=lambda r: (r.get("attributes") or {})
                      .get("releaseDate") or "", reverse=True)
    return sorted(rows, key=lambda r: r.get("first_seen") or 0, reverse=True)


# ---------------------------------------------------------- the engine

def last_played_index(store):
    """track id -> most recent play epoch, from the archive. Joined on both
    id spaces at use time (see the module docstring)."""
    conn = store._require_conn()
    with store._lock:
        rows = conn.execute(
            "SELECT track_id, MAX(started_at) FROM plays "
            "GROUP BY track_id").fetchall()
    return {r[0]: r[1] for r in rows}


class SmartlistScheduler(threading.Thread):
    """Re-evaluates every list on a cadence; materializes due ones.
    Evaluation is free (local); Apple is only touched for a due
    materialization while the renderer is healthy AND writes are on."""

    def __init__(self, store, browser_instance, interval=None,
                 materialize_fn=None):
        super().__init__(daemon=True, name="tonearm-smartlists")
        self.store = store
        self._browser = browser_instance
        self.interval = interval or config.smartlist_interval
        self._materialize = materialize_fn
        self._stop = threading.Event()

    def stop(self):
        self._stop.set()

    def _stalled(self):
        try:
            wd = self._browser.health()
        except Exception:
            return True
        if wd.get("last_ok") is False or \
                (wd.get("consecutive_failures") or 0) > 0:
            return True
        return False

    def run_once(self):
        """One sweep over all lists. Returns the summary; safe to call
        directly (tests do)."""
        materialize = self._materialize or materialize_list
        out = {"evaluated": 0, "synced": 0, "skipped_writes": 0,
               "throttled": 0, "errors": 0}
        for sl in self.store.smartlist_rows():
            out["evaluated"] += 1
            refresh_s = sl.get("refresh_s") or config.smartlist_min_refresh
            due = (not sl.get("last_sync")) or \
                time.time() - sl["last_sync"] >= refresh_s
            if not due:
                out["throttled"] += 1
                continue
            if not config.enable_writes:
                # evaluate anyway (free, keeps counts fresh), skip the PUT
                try:
                    matched = self._eval(sl)
                except Exception:
                    out["errors"] += 1
                    continue
                self.store.smartlist_update(sl["id"], last_eval=time.time(),
                                            last_count=len(matched))
                out["skipped_writes"] += 1
                continue
            if self._stalled():
                continue
            try:
                summary = materialize(sl)
                out["synced"] += 1
                log.info("smartlist %r synced: %d tracks -> %s",
                         sl["name"], summary["count"], summary["playlist_id"])
            except Exception as e:
                out["errors"] += 1
                log.warning("smartlist %r sync failed (kept alive): %s",
                            sl["name"], e)
        return out

    def _eval(self, sl):
        rows = self.store.library_rows()
        lp = last_played_index(self.store)
        matched = evaluate(rows, sl["rules"], last_played=lp)
        matched = sort_rows(matched, sl.get("sort"))
        cap = sl.get("limit") or 0
        if cap:
            matched = matched[:cap]
        return matched

    def run(self):
        log.info("smartlist scheduler armed: re-evaluate every %ds "
                 "(local eval; materialization writes-gated + throttled)",
                 self.interval)
        waited = 0.0
        while waited < 45 and not self._stop.wait(5):
            waited += 5
        while not self._stop.is_set():
            if self.store.enabled:
                try:
                    self.run_once()
                except Exception as e:
                    log.warning("smartlist sweep failed (kept alive): %s", e)
            slept = 0.0
            while slept < self.interval and not self._stop.is_set():
                self._stop.wait(min(5, self.interval - slept))
                slept += 5


def materialize_list(sl, store=None, mk_mod=None):
    """Make Apple match the evaluation: find-or-create the playlist, then
    ONE full-list PUT (#111). Raises SmartlistWritesDisabled when the
    writes gate is off — routes map that to the honest 501."""
    if not config.enable_writes:
        raise SmartlistWritesDisabled(
            "materializing touches Apple — set TONEARM_ENABLE_WRITES=1")
    store = store or _store()
    mk = mk_mod or _mk()
    rows = store.library_rows()
    lp = last_played_index(store)
    matched = evaluate(rows, sl["rules"], last_played=lp)
    matched = sort_rows(matched, sl.get("sort"))
    cap = sl.get("limit") or 0
    if cap:
        matched = matched[:cap]
    ids = [r["library_id"] for r in matched]
    pid = sl.get("playlist_id") \
        or mk.find_library_playlist(sl["name"])
    created = False
    if not pid:
        pid = mk.playlist_create(sl["name"],
                                 sl.get("description")
                                 or "tonearm smart playlist")
        created = True
    mk.playlist_set_tracks(pid, ids)
    store.smartlist_update(sl["id"], playlist_id=pid, last_sync=time.time(),
                           last_count=len(ids))
    try:
        from . import webhooks
        webhooks.emit(webhooks.SMARTLIST_UPDATED,
                      {"id": sl["id"], "name": sl["name"],
                       "playlist_id": pid, "created": created,
                       "count": len(ids)})
    except Exception as e:
        log.debug("smartlist.updated emit skipped: %s", e)
    return {"id": sl["id"], "name": sl["name"], "playlist_id": pid,
            "created": created, "count": len(ids)}


class SmartlistWritesDisabled(RuntimeError):
    """Raised by materialize_list when TONEARM_ENABLE_WRITES is off."""


def _store():
    from .store import store
    return store


def _mk():
    from . import musickit
    return musickit


def new_list_id():
    return "sl-" + uuid.uuid4().hex[:12]


# module-level singleton (set by main.py lifespan; tests may inspect it)
scheduler = None
