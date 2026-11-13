"""New-release watcher (v0.6 #42, #106-#108) — opt-in, VERIFY-LIVE GATE.

The loop: poll the LIBRARY artists, map each to a catalog artist, fetch the
artist's newest catalog album, and emit a `release.found` webhook when it is
newer than the last one seen. Optionally append the new album's tracks to a
playlist (#108 — writes-gated like every hand).

Design rules, the encoded kind:

* OFF by default (`TONEARM_WATCHER=1` to arm). The library-artist ->
  catalog-artist mapping is the UNDOCUMENTED Apple surface this was gated
  on: library artists are keyed `r.xxx` and nothing in the API doc states
  how to reach the catalog artist. The strategy implemented here is NAME
  SEARCH (`/v1/catalog/us/search?term=…&types=artists`) with a strict
  normalized-name match, cached per artist. It is honest about that: the
  README and ROADMAP both mark the mapping as unverified against a real
  account, and this whole feature ships disabled until that verification
  happens.
* **The first pass is always a silent baseline** (same discipline as the
  store's `library.changed`): a watcher that boots and screams "new
  release!" forty times is lying — it merely met forty artists. State is
  only recorded on the baseline; emissions start on the pass AFTER.
* **Bounded** (#106): at most `TONEARM_WATCHER_MAX_ARTISTS` artists get a
  catalog lookup per pass, walked in library order; cached mappings and
  seen-releases mean later passes rotate through the rest. One page
  (~100) of library artists per pass, a handful of evals per artist.
* **Stall-gated**: no pass starts while the watchdog reports a stall —
  the same rule as the digest and the snapshot walk.
* **Zero new eval kinds**: every Apple touch goes through `mk.api_music`
  (the existing amp-api fetch eval) and, for auto-add, the existing
  playlist mutations. No new JS is introduced anywhere.
* Never raises: a failed pass logs and waits for the next cadence.
"""
import logging
import re
import threading
import time
import unicodedata

from .config import config

log = logging.getLogger("tonearm.watcher")

FIRST_RUN_DELAY_S = 60       # let the renderer come up before the first pass
WATCHER_TIME_BUDGET_S = 180  # a pass stops here even under 429 backoffs
                             # (#176: a bounded pass once stretched to 4m40)

ALBUMS_PER_ARTIST = 10       # newest-N albums fetched per artist per pass
TRACKS_PER_ADD_CAP = 100     # auto-add never POSTs more than a page

# library "artists" are often COLLABORATIONS ("Alan Walker & Ava Max") —
# no catalog artist has that name. The release page a collab lands on is
# the PRIMARY (first-listed) artist's, so the mapping falls back to the
# first segment (verified live: solo names map ~always; bare full-name
# search mapped 55/100 — nearly every miss was an "&"/"," string)
_COLLAB_SPLIT = re.compile(r"\s*(?:&|,|feat\.?|ft\.?|with|x)\s+", re.I)


def name_candidates(name):
    """Full name first, then the primary (first-listed) artist of a collab
    string — nothing else: segments after the first are guests."""
    parts = _COLLAB_SPLIT.split(name or "", 1)
    out = [name] if (name or "").strip() else []
    if len(parts) > 1 and parts[0].strip():
        out.append(parts[0].strip())
    return out


def norm_name(s):
    """Casefold + strip accents; punctuation runs become separators —
    "Beyoncé" and "beyonce" are the same artist, "AC/DC" is "ac dc".
    A strict normalized-name match is what makes the mapping honest:
    "The Weeknd" and "Weeknd, The" are NOT the same string and must not
    silently map to each other."""
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore")\
        .decode("ascii")
    s = "".join(ch if (ch.isalnum() or ch.isspace()) else " " for ch in s)
    return " ".join(s.casefold().split())


def newest_album(albums):
    """The newest album by Apple's releaseDate (ISO strings compare
    lexicographically; Apple sometimes emits partial dates like '2026' —
    a full date always beats its own year prefix, which is the right
    direction). Returns None for no data, not a guess."""
    best = None
    for a in albums:
        d = (a.get("attributes") or {}).get("releaseDate") or ""
        if not d:
            continue
        if best is None or d > best[0]:
            best = (d, a)
    if best is None:
        return None
    a = best[1]
    return {"id": a.get("id"),
            "name": (a.get("attributes") or {}).get("name"),
            "release_date": best[0]}


class ReleaseWatcher(threading.Thread):
    """One flat daemon thread; `mk_mod` and `emit_fn` are injected so tests
    drive it hermetically (the digest pattern)."""

    def __init__(self, store, browser_instance, mk_mod, interval=None,
                 emit_fn=None, max_artists=None, time_budget_s=None):
        super().__init__(daemon=True, name="tonearm-watcher")
        self.store = store
        self._browser = browser_instance
        self._mk = mk_mod
        self.interval = interval or config.watcher_interval
        self._emit = emit_fn
        self.max_artists = max_artists or config.watcher_max_artists
        self.time_budget_s = time_budget_s or WATCHER_TIME_BUDGET_S
        self._busy = threading.Lock()      # single-flight: passes never overlap
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

    # ------------------------------------------------------------ the pass

    def run_pass(self):
        """One bounded pass. Returns a summary; safe to call directly
        (the thread calls this; so does POST /api/watcher/refresh).
        Two bounds: the artist budget (max_artists) AND a wall-clock
        budget (#176 — under 429 backoffs a bounded 100-artist pass
        stretched to 4m40s and outlived every client timeout)."""
        if not self._busy.acquire(timeout=0.1):
            return {"ran": False, "reason": "previous pass still running"}
        try:
            t0 = time.time()
            artists = self._walk_artists()
            summary = {"ran": True,
                       "artists_seen": len(artists),
                       "checked": 0, "mapped": 0, "unmapped": 0,
                       "new_releases": 0, "auto_added": 0}
            budget = self.max_artists
            for art in artists:
                if budget <= 0:
                    summary["skipped_budget"] = True
                    break
                if time.time() - t0 > self.time_budget_s:
                    summary["time_budget_exhausted"] = True
                    break
                try:
                    checked = self._check_artist(art, summary)
                except Exception as e:
                    # one bad artist never kills the pass
                    log.debug("watcher: %s check failed: %s",
                              art.get("name"), e)
                    continue
                if checked:
                    summary["checked"] += 1
                    budget -= 1
                    # `checked` = consumed a catalog lookup (mapping attempt
                    # or albums fetch) — that's what the budget bounds
            summary["seconds"] = round(time.time() - t0, 1)
            summary["completed_at"] = time.time()
            try:
                self.store.set_cursor("watcher.pass", summary)
            except Exception as e:             # store off: pass still ran
                log.debug("watcher cursor skipped: %s", e)
            return summary
        finally:
            self._busy.release()

    def _walk_artists(self):
        """Library artists, one page is enough for the bound. `item_row`
        normalizes: id (r.xxx / mock m.arN) + name."""
        def extract(data):
            return [self._mk.item_row(t) for t in data.get("data", [])]
        return self._mk.paginated("/v1/me/library/artists?limit=100",
                                  extract, fresh=True)

    def _catalog_artist(self, artist_id, name):
        """The mapping, cached in the store (negative results are retried
        next pass — a name search can fail on a blip; a WRONG match must
        not be cached: only a strict name match lands). Collab strings
        fall back to their primary artist (see name_candidates)."""
        state = self.store.watcher_artist(artist_id)
        if state and state.get("catalog_artist_id"):
            return state["catalog_artist_id"]
        for candidate in name_candidates(name):
            hits = self._mk.api_music(
                f"/v1/catalog/us/search?term={_urlquote(candidate)}"
                f"&types=artists&limit=5").get("results", {})\
                .get("artists", {}).get("data", [])
            want = norm_name(candidate)
            for h in hits:
                if norm_name((h.get("attributes") or {}).get("name")) == want:
                    self.store.watcher_upsert_artist(
                        artist_id, name, catalog_artist_id=h["id"],
                        catalog_artist_name=(h.get("attributes") or {})
                        .get("name"))
                    return h["id"]
        # honest miss: record the attempt so /api/watcher can show it
        self.store.watcher_upsert_artist(artist_id, name)
        return None

    def _check_artist(self, art, summary):
        """Map + fetch newest release + diff. Returns True if the artist
        consumed catalog budget this pass."""
        artist_id, name = art.get("library_id") or art.get("id"), \
            art.get("name") or ""
        if not artist_id:
            return False
        state = self.store.watcher_artist(artist_id)
        # unmapped artists get first claim on the budget
        need_mapping = not (state and state.get("catalog_artist_id"))
        catalog_id = self._catalog_artist(artist_id, name)
        if not catalog_id:
            summary["unmapped"] += 1
            return need_mapping
        summary["mapped"] += 1
        res = self._mk.api_music(
            f"/v1/catalog/us/artists/{catalog_id}/albums?limit={ALBUMS_PER_ARTIST}")
        fresh = newest_album(res.get("data", []))
        if fresh is None or not fresh.get("id"):
            return True         # the lookup happened; it consumed budget
        prev = state.get("last_album_id") if state else None
        if prev is None:
            # baseline: record silently — see the module docstring
            self.store.watcher_upsert_artist(
                artist_id, name, last_album_id=fresh["id"],
                last_album_name=fresh.get("name"),
                last_release_date=fresh.get("release_date"))
            return True          # the lookup happened; it consumed budget
        if fresh["id"] == prev:
            return True          # unchanged — and it still cost a lookup
        if _date_gt(fresh.get("release_date"),
                    state.get("last_release_date")):
            self._announce(artist_id, name, catalog_id, fresh, state, summary)
        else:
            # a different album but not newer (a reissue reshuffle etc.) —
            # keep the newer date, no event
            self.store.watcher_upsert_artist(
                artist_id, name, last_album_id=fresh["id"],
                last_album_name=fresh.get("name"),
                last_release_date=fresh.get("release_date"))
        return True

    def _announce(self, artist_id, artist, catalog_id, album, state, summary):
        """Emit `release.found` and, if configured AND writes are on,
        append the album's tracks to the target playlist (#108)."""
        payload = {"artist_id": artist_id, "artist": artist,
                   "catalog_artist_id": catalog_id,
                   "album_id": album["id"], "album": album.get("name"),
                   "release_date": album.get("release_date"),
                   "previous": {"album_id": state.get("last_album_id"),
                                "album": state.get("last_album_name"),
                                "release_date": state.get("last_release_date")}}
        target = config.watcher_auto_playlist
        if target and config.enable_writes:
            try:
                payload["auto_added_to"] = self._auto_add(album, target)
                summary["auto_added"] += 1
            except Exception as e:
                payload["auto_add_error"] = str(e)[:200]
                log.warning("watcher auto-add failed: %s", e)
        elif target:
            payload["auto_add_skipped"] = "TONEARM_ENABLE_WRITES is off"
        self._emit_event("release.found", payload)
        summary["new_releases"] += 1
        log.info("watcher: %s — new release %r (%s)", artist,
                 album.get("name"), album.get("release_date"))
        self.store.watcher_upsert_artist(
            artist_id, artist, last_album_id=album["id"],
            last_album_name=album.get("name"),
            last_release_date=album.get("release_date"))

    def _auto_add(self, album, playlist_name):
        """Find-or-create the target playlist, add the album's tracks
        (catalog song ids — Apple wraps them into the library)."""
        mk = self._mk
        pid = mk.find_library_playlist(playlist_name) \
            or mk.playlist_create(playlist_name,
                                  "new releases (tonearm watcher)")
        tracks = mk.paginated(
            f"/v1/catalog/us/albums/{album['id']}/tracks?limit=100",
            lambda d: [mk.song_row(t) for t in d.get("data", [])],
            fresh=True)
        ids = [t["id"] for t in tracks if t.get("id")][:TRACKS_PER_ADD_CAP]
        if ids:
            mk.playlist_add_tracks(pid, ids)
        return pid

    def _emit_event(self, event_type, payload):
        emit = self._emit
        if emit is None:
            from . import webhooks
            emit = webhooks.emit
        emit(event_type, payload)

    def _boot_pass_fresh(self):
        """True when the last completed pass is recent enough that running
        another at boot would just burn Apple's rate budget (#176, found
        live: six debug restarts -> six boot passes -> the 429 wall ->
        playback and search starved for a long window). Fresh = within
        half the interval."""
        try:
            last = self.store.get_cursor("watcher.pass") or {}
            done = last.get("completed_at") or 0
        except Exception:
            return False
        return done > 0 and (time.time() - done) < self.interval / 2

    def run(self):
        log.info("release watcher armed: library-artists poll every %ds, "
                 "max %d catalog lookups/pass, %ds time budget "
                 "(stall-gated, single-flight; mapping strategy: name "
                 "search — LIVE-VERIFIED)", self.interval, self.max_artists,
                 self.time_budget_s)
        waited = 0.0
        while waited < FIRST_RUN_DELAY_S and not self._stop.wait(5):
            waited += 5
        if self._boot_pass_fresh():
            log.info("watcher: last pass is fresh — skipping the boot pass "
                     "(#176: restarts must not stampede the rate budget)")
        while not self._stop.is_set():
            if not self._stalled():
                try:
                    summary = self.run_pass()
                    if summary.get("ran") and summary.get("new_releases"):
                        log.info("watcher pass: %d new release(s)",
                                 summary["new_releases"])
                except Exception as e:
                    log.warning("watcher pass failed (kept alive): %s", e)
            slept = 0.0
            while slept < self.interval and not self._stop.is_set():
                self._stop.wait(min(5, self.interval - slept))
                slept += 5


def _date_gt(a, b):
    """True when date a is strictly newer than date b. ISO strings compare
    lexicographically; missing b (baseline) is always older."""
    if not a:
        return False
    return not b or a > b


def _urlquote(s):
    import urllib.parse
    return urllib.parse.quote(s or "", safe="")


# module-level singleton (set by main.py lifespan; tests may inspect it)
watcher = None
