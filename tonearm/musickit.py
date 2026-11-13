"""JavaScript builders for driving MusicKit inside the page.

Every snippet is IIFE-wrapped (Chrome persists top-level declarations between
evals — a redeclaration is fatal). Async snippets are awaited by the CDP layer.
"""
import json
import logging
import re
import time

from . import cache as _cache_mod
from .browser import browser, BrowserError
from .config import config
from .metrics import METRICS

read_cache = _cache_mod.read_cache

# the Apple session's state, as far as OUR calls can tell (#189): "ok"
# after any 200, "expired" after Apple's 403/40300 (Invalid
# authentication — the session died; the fix is `python -m tonearm
# login`), "unknown" before the first call. /health surfaces it.
session_state = {"state": "unknown", "since": 0.0}


def _note_session(status, body):
    if status == 200:
        if session_state["state"] != "ok":
            session_state.update(state="ok", since=time.time())
    elif status == 403 and "40300" in (body or "")[:400]:
        if session_state["state"] != "expired":
            session_state.update(state="expired", since=time.time())
            log.warning("apple session EXPIRED (403 40300) — run "
                        "`python -m tonearm login` to re-authenticate")

log = logging.getLogger("tonearm.musickit")


def _j(value):
    return json.dumps(value)


# ---------------------------------------------------------------- primitives

def api_music(path, timeout=90, fresh=False):
    """GET any me/catalog path with tokens injected. Uses raw fetch instead of
    MusicKit's api.music because the latter memoizes responses — reads after
    mutations would return stale data.
    Reads go through the TTL cache + single-flight coalescer (see cache.py);
    `fresh=True` bypasses it (clients: `?fresh=1` on the favorites/ratings
    routes) — for when Apple's own auto-sync lag makes even a 10s TTL lie."""
    res = raw_api(path, method="GET", timeout=timeout, fresh=fresh)
    _note_session(res["status"], res["body"])
    if res["status"] != 200:
        raise BrowserError(f"apple api: HTTP {res['status']} — {res['body'][:150]}")
    return json.loads(res["body"])


def _raw_api_now(path, method="GET", body=None, timeout=60):
    """Raw amp-api call with tokens injected. Full control of method + body.
    Mutations bust the read cache and open the grace window BEFORE issuing —
    Apple applies them async (202/204), and retried reads must never be
    served the pre-mutation snapshot from cache."""
    if method != "GET":
        read_cache.after_mutation()
    res = browser.eval(
        f"""(async () => {{
          const inst = MusicKit.getInstance();
          const init = {{
            method: {_j(method)},
            headers: {{ 'Authorization': 'Bearer ' + inst.developerToken,
                       'Media-User-Token': inst.musicUserToken,
                       'Origin': 'https://music.apple.com' }},
          }};
          {f'init.body = {_j(json.dumps(body))};' if body is not None else ''}
          const res = await fetch('https://amp-api.music.apple.com' + {_j(path)}, init);
          return {{status: res.status,
                   retryAfter: res.headers.get('Retry-After'),
                   body: await res.text()}};
        }})()""", timeout=timeout)
    METRICS.inc("tonearm_apple_requests_total", {"code": f"{res['status'] // 100}xx"},
                help_text="amp-api responses by status class")
    if res["status"] == 429:
        METRICS.inc("tonearm_apple_429_total",
                    help_text="Apple rate-limit hits (Retry-After honored in "
                              "the fetch layer)")
    return res


def raw_api(path, method="GET", body=None, timeout=60, fresh=False):
    """raw_api with the read cache in front of GETs (single-flight coalesced;
    never applied to mutations — and only 200s are ever cached: a cached 404
    or 429 would serve a not-yet-applied snapshot across Apple's async
    mutation window). GETs that hit Apple's 429 rate limit back off honoring
    Retry-After, bounded. Mutations NEVER auto-retry: a wrong-key favorites
    DELETE returns 204 and does NOTHING — blind retries would mask state."""
    if method != "GET":
        return _raw_api_now(path, method, body, timeout)
    fetch = lambda: _get_with_backoff(path, body, timeout)
    if not read_cache.enabled or fresh:
        return fetch()
    return read_cache.coalesce(path, fetch,
                               cache_when=lambda res: res.get("status") == 200)


_BACKOFF_TRIES = 3
_BACKOFF_CAP_S = 5.0          # Retry-After can be huge; the eval timeout
                              # bounds total latency, this bounds the sleeps


def _get_with_backoff(path, body, timeout):
    """Bounded 429 backoff for GETs. FLAT — a loop of independent evals, each
    acquiring the browser lock fresh; never a nested/reconnect cascade.
    Sleeps happen OUTSIDE the lock, so other callers proceed while we wait."""
    res = _raw_api_now(path, "GET", body, timeout)
    for attempt in range(_BACKOFF_TRIES - 1):
        if res["status"] != 429:
            return res
        try:
            ra = float(res.get("retryAfter") or 0)
        except (TypeError, ValueError):
            ra = 0.0
        delay = min(ra, _BACKOFF_CAP_S) if ra else 0.5 * (attempt + 1)
        time.sleep(delay)
        log.warning("apple 429 on %s — retry %d/%d after %.1fs",
                    path[:90], attempt + 1, _BACKOFF_TRIES - 1, delay)
        res = _raw_api_now(path, "GET", body, timeout)
    return res


# ---------------------------------------------------------------- library

def paginated(first_path, extract, fresh=False):
    """Walk Apple's paging (`next` links) and concatenate extracted items.
    NOTE: Apple's `next` links drop the `limit` param (defaulting to 25/page)
    — re-apply the original limit so big libraries don't take 4x the calls."""
    import re as _re
    m = _re.search(r"[?&]limit=(\d+)", first_path)
    limit = m.group(1) if m else None
    out, path, guard = [], first_path, 0
    while path and guard < 1000:
        data = api_music(path if path.startswith("/") else "/" + path, fresh=fresh)
        out.extend(extract(data))
        nxt = data.get("next")
        if nxt and limit and "limit=" not in nxt:
            sep = "&" if "?" in nxt else "?"
            nxt = f"{nxt}{sep}limit={limit}"
        path = nxt if nxt and nxt.startswith("/") else ("/" + nxt if nxt else None)
        guard += 1
    return out


def song_row(t):
    """Normalize a library/catalog song object."""
    attrs = t.get("attributes", {}) or {}
    art = (attrs.get("artwork") or {}).get("url", "")
    if art:
        # Apple templates: .../{w}x{h}bb.jpg -> pick 600x600
        art = art.replace("{w}", "600").replace("{h}", "600")
    params = attrs.get("playParams") or {}
    return {
        "id": params.get("catalogId") or t.get("id"),
        "library_id": t.get("id"),
        "catalog_id": params.get("catalogId"),
        "name": attrs.get("name"),
        "artist": attrs.get("artistName"),
        "album": attrs.get("albumName"),
        "artwork": art or None,
        "duration_ms": attrs.get("durationInMillis"),
    }


def item_row(t):
    """Normalize ANY library/catalog resource (song, album, artist, playlist…).
    Normalized top-level fields plus the raw attributes blob — nothing hidden."""
    row = song_row(t)
    attrs = t.get("attributes", {}) or {}
    art = (attrs.get("artwork") or {}).get("url", "")
    row.update({
        "type": t.get("type"),
        "artwork": art.replace("{w}", "600").replace("{h}", "600") if art else None,
        "track_number": attrs.get("trackNumber"),
        "play_count": attrs.get("playCount"),
        "release_date": attrs.get("releaseDate"),
        "genres": attrs.get("genreNames"),
        "attributes": attrs,   # full, unfiltered — every field Apple exposes
    })
    return row


def playlist_tracks(playlist_id, fresh=False):
    """All tracks of a library playlist. Empty playlists 404 on their
    tracks relationship (Apple treats 'no tracks' as 'no related
    resources') — that's [], not an error.
    `fresh=True` bypasses the read cache (favorites auto-sync lag)."""
    def extract(data):
        return [song_row(t) for t in data.get("data", [])]
    try:
        return paginated(f"/v1/me/library/playlists/{playlist_id}/tracks?limit=100",
                         extract, fresh=fresh)
    except BrowserError as e:
        if "404" in str(e):
            return []
        raise


def find_library_playlist(name, fresh=False):
    """Find a library playlist by (case-insensitive) name.
    NOTE: no `match=` param — it's a MusicKit-client-only extension; the raw
    amp-api rejects it. Filter locally instead."""
    hits = paginated("/v1/me/library/playlists?limit=100",
                     lambda d: d.get("data", []), fresh=fresh)
    for pl in hits:
        if (pl.get("attributes", {}).get("name") or "").lower() == name.lower():
            return pl["id"]
    return None


def _re_quote(s):
    return re.escape(s)


# ---------------------------------------------------------------- favorites

FAVORITES_TMPL = {
    "catalog": "https://amp-api.music.apple.com/v1/me/favorites?art%5Burl%5D=f&ids%5Bsongs%5D={id}",
    "library": "https://amp-api.music.apple.com/v1/me/favorites?art%5Burl%5D=f&ids%5Blibrary-songs%5D={id}",
}


def set_favorite(kind, resource_id, favorited):
    """(un)favorite a song. kind: 'catalog' | 'library'.

    NOTE: discovered empirically. Apple's player uses
      POST/DELETE .../favorites?ids[songs]=<catalogId>            for catalog songs
      POST/DELETE .../favorites?ids[library-songs]=<libId>        for library-keyed songs
    The DELETE returns 204 even when it no-ops, so verify externally.
    """
    url = FAVORITES_TMPL[kind].format(id=resource_id)
    method = "POST" if favorited else "DELETE"
    read_cache.after_mutation()          # bust + grace BEFORE issuing
    res = browser.eval(
        f"""(async () => {{
          const inst = MusicKit.getInstance();
          const r = await fetch({_j(url)}, {{
            method: {_j(method)},
            headers: {{ 'Authorization': 'Bearer ' + inst.developerToken,
                       'Media-User-Token': inst.musicUserToken,
                       'Origin': 'https://music.apple.com' }}
          }});
          return r.status;
        }})()""", timeout=30)
    if res not in (200, 201, 202, 204):
        raise BrowserError(f"favorites {method} -> HTTP {res}")


# ---------------------------------------------------------------- ratings

def rate_song(song_id, like):
    """like=True -> PUT value 1; like=None -> DELETE (clear).
    NOTE: this endpoint only accepts value 1 (like) in practice — a dislike
    value is accepted but stores as 1, so it is not exposed."""
    if like is None:
        res = raw_api(f"/v1/me/ratings/songs/{song_id}", method="DELETE")
    else:
        res = raw_api(f"/v1/me/ratings/songs/{song_id}", method="PUT",
                      body={"type": "ratings", "attributes": {"value": 1}})
    if res["status"] not in (200, 204):
        raise BrowserError(f"rating -> HTTP {res['status']}: {res['body'][:120]}")
    return res["status"]


def get_rating(song_id, fresh=False):
    """Current rating: None = none, 1 = like. `fresh=True` bypasses the
    read cache (ratings lag server-side; a heart IS this same value)."""
    res = raw_api(f"/v1/me/ratings/songs/{song_id}", method="GET", fresh=fresh)
    if res["status"] == 404:
        return None
    if res["status"] != 200:
        raise BrowserError(f"rating GET -> HTTP {res['status']}")
    return json.loads(res["body"])["data"][0]["attributes"].get("value")


# ---------------------------------------------------------------- library adds

def library_add(catalog_ids):
    """Add catalog songs to the library. Returns 202 (async!) — Apple applies
    it a beat later; verify by listing."""
    res = raw_api(f"/v1/me/library?ids[songs]={','.join(catalog_ids)}", method="POST")
    if res["status"] not in (200, 202):
        raise BrowserError(f"library add -> HTTP {res['status']}: {res['body'][:120]}")
    return res["status"]


def library_remove(library_song_ids):
    """Remove songs from the library (NOT the same as unfavoriting!)."""
    out = []
    for lid in library_song_ids:
        res = raw_api(f"/v1/me/library/songs/{lid}", method="DELETE")
        if res["status"] != 204:
            raise BrowserError(f"library remove {lid} -> HTTP {res['status']}")
        out.append(lid)
    return out


def library_add_albums(catalog_album_ids):
    """Add catalog ALBUMS (and their tracks) to the library. 202-async."""
    res = raw_api(f"/v1/me/library?ids[albums]={','.join(catalog_album_ids)}",
                  method="POST")
    if res["status"] not in (200, 202):
        raise BrowserError(f"library add albums -> HTTP {res['status']}: "
                           f"{res['body'][:120]}")
    return res["status"]


def library_remove_album(library_album_id):
    """Remove a whole library album (l.XXX). This deletes all its songs."""
    res = raw_api(f"/v1/me/library/albums/{library_album_id}", method="DELETE")
    if res["status"] != 204:
        raise BrowserError(f"library remove album -> HTTP {res['status']}")
    return res["status"]


# ---------------------------------------------------------------- playlists

def playlist_create(name, description=""):
    body = {"attributes": {"name": name, "description": description},
            "relationships": {"tracks": {"data": []}}}
    res = raw_api("/v1/me/library/playlists", method="POST", body=body)
    if res["status"] != 201:
        raise BrowserError(f"playlist create -> HTTP {res['status']}: {res['body'][:150]}")
    return json.loads(res["body"])["data"][0]["id"]


def playlist_add_tracks(playlist_id, catalog_ids):
    """Append catalog songs (auto-wrapped into the library by Apple)."""
    res = raw_api(f"/v1/me/library/playlists/{playlist_id}/tracks", method="POST",
                  body={"data": [{"id": cid, "type": "songs"} for cid in catalog_ids]})
    if res["status"] not in (200, 204):
        raise BrowserError(f"playlist add -> HTTP {res['status']}: {res['body'][:150]}")
    return res["status"]


def playlist_set_tracks(playlist_id, library_ids):
    """REPLACE the playlist's track list, in the given order.
    This one call covers reorder (same list, new order) and removal
    (omit tracks) — there is no separate delete-track endpoint that works;
    DELETE .../tracks always 400s ('No mode supplied')."""
    res = raw_api(f"/v1/me/library/playlists/{playlist_id}/tracks", method="PUT",
                  body={"data": [{"id": lid, "type": "library-songs"}
                                 for lid in library_ids]})
    if res["status"] not in (200, 204):
        raise BrowserError(f"playlist set -> HTTP {res['status']}: {res['body'][:150]}")
    return res["status"]


def playlist_rename(playlist_id, name=None, description=None):
    attrs = {}
    if name is not None:
        attrs["name"] = name
    if description is not None:
        attrs["description"] = description
    res = raw_api(f"/v1/me/library/playlists/{playlist_id}", method="PATCH",
                  body={"attributes": attrs})
    if res["status"] not in (200, 204):
        raise BrowserError(f"playlist rename -> HTTP {res['status']}: {res['body'][:150]}")
    return res["status"]


def playlist_delete(playlist_id):
    res = raw_api(f"/v1/me/library/playlists/{playlist_id}", method="DELETE")
    if res["status"] != 204:
        raise BrowserError(f"playlist delete -> HTTP {res['status']}")
    return res["status"]


# ---------------------------------------------------------------- queue

def queue_add(catalog_id, play_next=False):
    fn = "playNext" if play_next else "playLater"
    browser.eval(
        f"""(async () => {{
          const mk = MusicKit.getInstance();
          await mk.{fn}({{songs: [{_j(catalog_id)}]}});
          return true;
        }})()""", timeout=30)


def queue_reorder(ids):
    """Reorder the queue to EXACTLY this list (#87: the client sends the
    whole ordered list, never deltas — last write wins, no merge states).
    MusicKit has no public reorder: setQueue(songs) rebuilds the queue,
    then playback is moved back onto the SAME track at its new index and
    resumed if it was playing. setQueue takes the SONGS qualifier for bare
    catalog ids ({items} with raw id strings is rejected: MKError mk-007
    Invalid media URL — found live); setQueue STOPS the player and
    _queueItems fills in asynchronously — so: settle, find the index,
    changeToMediaAtIndex, play() if it was playing. The track restarts
    from its top (a rebuilt queue has no seekable past) — best-effort,
    like every transport op; a failed eval leaves the old queue alone."""
    id_list = ", ".join(_j(i) for i in ids)
    browser.eval(
        f"""(async () => {{
          const mk = MusicKit.getInstance();
          const cur = mk.nowPlayingItem
                      && (mk.nowPlayingItem.id
                          || mk.nowPlayingItem.attributes?.playParams?.id);
          const wasPlaying = !!mk.isPlaying;
          await mk.setQueue({{songs: [{id_list}]}});
          // _queueItems fills in ASYNCHRONOUSLY (Apple fetches the songs'
          // metadata) — poll until it settles (~3s worst case) or the
          // index search silently mis-lands on 0 (found live)
          let items = [];
          for (let n = 0; n < 20; n++) {{
            await new Promise(r => setTimeout(r, 150));
            items = (mk._playbackController?._queue?._queueItems
                     || mk._playbackController?._queue?.items
                     || mk.queue?._queueItems || mk.queue?.items || []);
            if (items.length >= {len(ids)}) break;
          }}
          // _queueItems entries WRAP the item (e.item || e — same unwrap
          // the queue route uses); nowPlayingItem is the bare MediaItem
          const key = it => {{
            const t = it?.item || it;
            return t?.id || t?.attributes?.playParams?.id;
          }};
          let idx = items.findIndex(it => key(it) === cur);
          if (idx < 0) idx = 0;                        // unknown -> top
          if (idx > 0 && mk.changeToMediaAtIndex)
            await mk.changeToMediaAtIndex(idx);
          if (wasPlaying && mk.play) await mk.play();
          return {{idx, items: items.length, wasPlaying}};
        }})()""", timeout=30)


# ---------------------------------------------------------------- playback
# The web player's MusicKit build exposes transport methods directly on the
# instance (no `.player` sub-object): play, pause, skipToNextItem,
# skipToPreviousItem, volume, and a private _queue with nowPlayingItem.

def playback_command(cmd):
    calls = {
        "play": "mk.play()",
        "pause": "mk.pause()",
        "toggle": "mk.isPlaying ? mk.pause() : mk.play()",
        "next": "mk.skipToNextItem()",
        "previous": "mk.skipToPreviousItem()",
    }
    if cmd not in calls:
        raise BrowserError(f"unknown playback command {cmd!r}")
    browser.eval(
        f"""(async () => {{
          const mk = MusicKit.getInstance();
          try {{ await {calls[cmd]}; }} catch (e) {{ return {{warn: String(e).slice(0, 120)}}; }}
          return true;
        }})()""", timeout=15)


def playback_back(threshold_ms=10000):
    """The hardware-button 'back' (hardware-button gestures, sandbox era):
    past `threshold_ms`, 'back' means RESTART this song; before it,
    previous track. One eval, decided on-device-side by the server so the
    button stays dumb. MusicKit's own skipToPreviousItem restarts at ~3s —
    not the rule remote controls want."""
    return browser.eval("""(async () => {
      const mk = MusicKit.getInstance();
      const elapsed = (mk.currentPlaybackTime || 0) * 1000;
      if (elapsed > THRESHOLD) {
        try { await mk.seekToSeconds(0); return {back: "restart", elapsed}; }
        catch (e) {
          // older builds: rewind the playhead the crude way
          try { mk.currentPlaybackTime = 0; return {back: "restart-crude", elapsed}; }
          catch (e2) { return {warn: String(e2).slice(0, 120)}; }
        }
      }
      await mk.skipToPreviousItem();
      return {back: "previous", elapsed};
    })()""".replace("THRESHOLD", str(threshold_ms)), timeout=15)


def now_playing():
    return browser.eval("""(() => {
      const mk = MusicKit.getInstance();
      // mk.nowPlayingItem is the public, reliable source (the private queue
      // internals move around between builds). Fall back to the queue probe.
      let item = mk.nowPlayingItem;
      if (!item && mk._playbackController && mk._playbackController._queue) {
        const q = mk._playbackController._queue;
        const cur = q._queueItems && q._queueItems[q._nextPlayableItemIndex];
        item = cur && (cur.item || cur);
      }
      const art = item && item.attributes && item.attributes.artwork;
      return {
        isPlaying: !!mk.isPlaying,
        state: mk.playbackState,
        // catalog id when the queue holds one; library rows carry their
        // library id — callers treat it as "playable-ish", not gospel
        id: item ? (item.id || item.attributes?.playParams?.id) || null : null,
        isLibrary: item ? !!String(item.id || "").startsWith("i.") : false,
        title: item ? (item.title || item.attributes?.name) : null,
        artist: item ? item.artistName : null,
        album: item ? (item.albumName || item.attributes?.albumName) : null,
        durationMs: item ? (item.playbackDurationMillis ||
                            item.attributes?.durationInMillis) : null,
        artworkUrl: art ? art.url.replace('{w}', '600').replace('{h}', '600') : null,
        progress: typeof mk.currentPlaybackProgress === 'number'
                  ? mk.currentPlaybackProgress : null,
        elapsedMs: mk.currentPlaybackTime != null
                   ? Math.round(mk.currentPlaybackTime * 1000) : null,
      };
    })()""", timeout=15)


# ---------------------------------------------------------------- streaming

STREAM_HOOK = """(() => {
  if (window.__tonearmHooked) return true;
  const mk = MusicKit.getInstance();
  window.__tonearmBuf = [];
  window.__tonearmSeq = 0;
  window.__tonearmLast = 0;
  const push = (ev) => {
    const now = Date.now();
    // progress fires constantly while playing — throttle to ~1/s
    if (ev === 'playbackProgressDidChange' && now - window.__tonearmLast < 950) return;
    window.__tonearmLast = now;
    const item = mk.nowPlayingItem || {};
    const attrs = item.attributes || {};
    const art = attrs.artwork || {};
    window.__tonearmBuf.push({
      seq: ++window.__tonearmSeq, ev, ts: now,
      isPlaying: !!mk.isPlaying, state: mk.playbackState,
      title: item.title || attrs.name || null,
      artist: item.artistName || null,
      album: item.albumName || attrs.albumName || null,
      id: item.id || null,
      durationMs: item.playbackDurationMillis || attrs.durationInMillis || null,
      elapsedMs: mk.currentPlaybackTime != null
                 ? Math.round(mk.currentPlaybackTime * 1000) : null,
      progress: typeof mk.currentPlaybackProgress === 'number'
                ? mk.currentPlaybackProgress : null,
      volume: typeof mk.volume === 'number' ? mk.volume : null,
      shuffle: mk.shuffle ?? null, repeat: mk.repeatMode ?? null,
      artworkUrl: art && art.url
                  ? art.url.replace('{w}', '600').replace('{h}', '600') : null,
    });
    if (window.__tonearmBuf.length > 300)
      window.__tonearmBuf.splice(0, window.__tonearmBuf.length - 300);
  };
  for (const e of ['playbackStateDidChange', 'nowPlayingItemDidChange',
                   'queueItemsDidChange', 'playbackProgressDidChange',
                   'shuffleModeDidChange', 'repeatModeDidChange']) {
    mk.addEventListener(e, () => push(e));
  }
  // headless/background tabs throttle MusicKit's own progress events to
  // nearly nothing — keep a steady ~5s tick so stream clients see the
  // playhead move even when the tab isn't firing
  setInterval(() => { if (mk.isPlaying) push('playbackProgressDidChange'); }, 5000);
  window.__tonearmHooked = true;
  return true;
})()"""


def install_stream_hook():
    browser.eval(STREAM_HOOK, timeout=15)


def drain_stream(after_seq=0):
    """Buffered player events with seq > after_seq (oldest first)."""
    return browser.eval("""(() => {
      const buf = window.__tonearmBuf || [];
      const after = arguments_after === undefined ? 0 : arguments_after;
      return buf.filter(e => e.seq > after);
    })()""".replace("arguments_after", str(after_seq)), timeout=15)


def snapshot():
    """Full player state — the first thing a stream client gets."""
    st = playback_settings()
    np = now_playing()
    st.update(np)
    st["queue"] = queue()
    return st


def play_song(catalog_id):
    browser.eval(
        f"""(async () => {{
          const mk = MusicKit.getInstance();
          await mk.setQueue({{songs: [{_j(catalog_id)}]}});
          await mk.play();
          return true;
        }})()""", timeout=30)


def queue():
    items = browser.eval("""(() => {
      const mk = MusicKit.getInstance();
      const q = mk._playbackController && mk._playbackController._queue;
      const items = q ? (q._queueItems || []) : [];
      return items.map(e => {
        const t = e.item || e;
        return {id: t.id, title: t.title, artist: t.artistName, kind: t.kind};
      });
    })()""", timeout=15)
    METRICS.gauge("tonearm_queue_depth_last", len(items or []),
                  help_text="Last-known playback queue depth (updated only "
                            "when the queue is actually read — never polled "
                            "at scrape time)")
    return items


def playback_property(name):
    return browser.eval(f"(() => MusicKit.getInstance()[{_j(name)}])()", timeout=10)


def set_playback_property(name, value):
    browser.eval(f"(() => {{ MusicKit.getInstance()[{_j(name)}] = {_j(value)}; }})()", timeout=10)


def playback_settings():
    return browser.eval("""(() => {
      const mk = MusicKit.getInstance();
      return {shuffle: mk.shuffle ?? null, repeat: mk.repeatMode ?? null,
              volume: typeof mk.volume === 'number' ? mk.volume : null,
              isPlaying: !!mk.isPlaying};
    })()""", timeout=10)


def play_collection(kind, resource_id):
    browser.eval(
        f"""(async () => {{
          const mk = MusicKit.getInstance();
          await mk.setQueue({{{_j(kind)}: {_j(resource_id)}}});
          await mk.play();
          return true;
        }})()""", timeout=30)


# ---------------------------------------------------------------- mock mode
# TONEARM_MOCK=1 swaps this whole surface for synthetic fixtures (see
# tonearm/mock.py). This MUST be the last thing in the module: install() needs
# every real function defined so the swap is complete.
if config.mock_enabled:
    import sys as _sys
    from .mock import install as _install_mock
    _mock = _install_mock(_sys.modules[__name__])
    log.info("MOCK MODE — serving synthetic fixtures, no Chrome, no Apple")
