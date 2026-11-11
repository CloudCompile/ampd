"""JavaScript builders for driving MusicKit inside the page.

Every snippet is IIFE-wrapped (Chrome persists top-level declarations between
evals — a redeclaration is fatal). Async snippets are awaited by the CDP layer.
"""
import json
import re

from .browser import browser, BrowserError


def _j(value):
    return json.dumps(value)


# ---------------------------------------------------------------- primitives

def api_music(path, timeout=90):
    """GET any me/catalog path with tokens injected. Uses raw fetch instead of
    MusicKit's api.music because the latter memoizes responses — reads after
    mutations would return stale data."""
    res = raw_api(path, method="GET", timeout=timeout)
    if res["status"] != 200:
        raise BrowserError(f"apple api: HTTP {res['status']} — {res['body'][:150]}")
    return json.loads(res["body"])


def raw_api(path, method="GET", body=None, timeout=60):
    """Raw amp-api call with tokens injected. Full control of method + body."""
    return browser.eval(
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
          return {{status: res.status, body: await res.text()}};
        }})()""", timeout=timeout)


# ---------------------------------------------------------------- library

def paginated(first_path, extract):
    """Walk Apple's paging (`next` links) and concatenate extracted items.
    NOTE: Apple's `next` links drop the `limit` param (defaulting to 25/page)
    — re-apply the original limit so big libraries don't take 4x the calls."""
    import re as _re
    m = _re.search(r"[?&]limit=(\d+)", first_path)
    limit = m.group(1) if m else None
    out, path, guard = [], first_path, 0
    while path and guard < 1000:
        data = api_music(path if path.startswith("/") else "/" + path)
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


def playlist_tracks(playlist_id):
    """All tracks of a library playlist (handles virtualization-free paging)."""
    def extract(data):
        return [song_row(t) for t in data.get("data", [])]
    return paginated(f"/v1/me/library/playlists/{playlist_id}/tracks?limit=100", extract)


def find_library_playlist(name):
    """Find a library playlist by (case-insensitive) name.
    NOTE: no `match=` param — it's a MusicKit-client-only extension; the raw
    amp-api rejects it. Filter locally instead."""
    hits = paginated("/v1/me/library/playlists?limit=100", lambda d: d.get("data", []))
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


def get_rating(song_id):
    res = raw_api(f"/v1/me/ratings/songs/{song_id}", method="GET")
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
  if (window.__ampdHooked) return true;
  const mk = MusicKit.getInstance();
  window.__ampdBuf = [];
  window.__ampdSeq = 0;
  window.__ampdLast = 0;
  const push = (ev) => {
    const now = Date.now();
    // progress fires constantly while playing — throttle to ~1/s
    if (ev === 'playbackProgressDidChange' && now - window.__ampdLast < 950) return;
    window.__ampdLast = now;
    const item = mk.nowPlayingItem || {};
    const attrs = item.attributes || {};
    const art = attrs.artwork || {};
    window.__ampdBuf.push({
      seq: ++window.__ampdSeq, ev, ts: now,
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
    if (window.__ampdBuf.length > 300)
      window.__ampdBuf.splice(0, window.__ampdBuf.length - 300);
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
  window.__ampdHooked = true;
  return true;
})()"""


def install_stream_hook():
    browser.eval(STREAM_HOOK, timeout=15)


def drain_stream(after_seq=0):
    """Buffered player events with seq > after_seq (oldest first)."""
    return browser.eval("""(() => {
      const buf = window.__ampdBuf || [];
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
    return browser.eval("""(() => {
      const mk = MusicKit.getInstance();
      const q = mk._playbackController && mk._playbackController._queue;
      const items = q ? (q._queueItems || []) : [];
      return items.map(e => {
        const t = e.item || e;
        return {id: t.id, title: t.title, artist: t.artistName, kind: t.kind};
      });
    })()""", timeout=15)


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
