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
    """GET via MusicKit's own client (handles auth + paging metadata)."""
    data = browser.eval(
        f"""(async () => {{
          const inst = MusicKit.getInstance();
          const res = await inst.api.music({_j(path)});
          return res.json;
        }})()""", timeout=timeout)
    if isinstance(data, dict) and data.get("errors"):
        raise BrowserError(f"apple api: {data['errors'][0].get('detail', data['errors'][0])}")
    return data


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
    """Walk Apple's paging (`next` links) and concatenate extracted items."""
    out, path, guard = [], first_path, 0
    while path and guard < 50:
        data = api_music(path if path.startswith("/") else "/" + path)
        out.extend(extract(data))
        nxt = data.get("next")
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
    """Find a library playlist by (case-insensitive) name."""
    hits = paginated(f"/v1/me/library/playlists?limit=100&match=/^{_re_quote(name)}$/i",
                     lambda d: d.get("data", []))
    if not hits:
        # match= filter is unreliable for library; fall back to a full scan
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
    if res not in (200, 204):
        raise BrowserError(f"favorites {method} -> HTTP {res}")


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
      const item = mk._queue && mk._queue.nowPlayingItem;
      return {
        isPlaying: !!mk.isPlaying,
        title: item ? item.title : null,
        artist: item ? item.artistName : null,
        album: item ? item.albumName : null,
        durationMs: item ? item.playbackDurationMillis : null,
      };
    })()""", timeout=15)


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
      const q = mk._queue || {};
      return (q._items || q.items || []).map(t => ({
        id: t.id, title: t.title, artist: t.artistName}));
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
