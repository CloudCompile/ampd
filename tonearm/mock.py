"""Mock mode (v0.4 #33): TONEARM_MOCK=1 serves the whole API from synthetic,
seeded fixtures — no Apple account, no Chrome tab, no network.

Design rules:
* **Fully synthetic.** Nothing here is recorded from a real account: names
  are generated ("Mock Artist 01"), artwork is None, ids are made up. The
  repo must never ship anyone's library.
* **Mock at the amp-api boundary, not the route layer.** The fake responses
  are APPLE-SHAPED raw dicts (attributes, playParams, relationships), so the
  real `mk.song_row` / `mk.item_row` normalizers and every route run
  UNCHANGED — a mock that bypassed the normalizers would test nothing.
* **Stateful where it teaches.** Playback is a state machine with a real
  synthetic playhead (elapsed advances with wall clock; tracks advance when
  they "end"); writes mutate the fake library. UI devs get a world that
  behaves, not a snapshot.
* **Model conformance harness** (#83): every raw fixture, run through the
  REAL normalizers, must validate against the response models — see
  tests/test_mock.py. If a fixture rots out of the model shape, CI fails.
* Wiring is one `install()` call at the bottom of musickit.py (mock mode
  swaps the mk surface; routes keep calling `mk.anything`). Chrome machinery
  is never *driven*: the watchdog doesn't arm, audio 404s honestly (#80).
"""
import random
import re
import threading
import time
import urllib.parse

from .browser import BrowserError
from .config import config

SEED = 0xA4D  # fixed — the fake library is identical on every boot

_ARTISTS = ["Mock Artist {}".format(i + 1) for i in range(6)]
_ALBUM_TITLES = ["Synth Sessions", "Plastic Fields", "Night Bus",
                 "Glass Arcade", "Slow Neon", "Paper Static"]
_SONG_WORDS = ["Signal", "Vapor", "Meridian", "Copper", "Lantern", "Drift",
               "Parallax", "Fountain", "Cinder", "Harbor", "Golden Hour",
               "Static Bloom", "Long Division", "Winter Index"]
_LYRIC_LINES = ["we tune the instruments of the night",
                "a city drawn in carbon paper",
                "hold the note until the room agrees",
                "every streetlamp is a slow metronome",
                "the chorus is a door left open",
                "count the bridges, forget the names"]


class MockKit:
    """Stateful fake of the musickit surface. All state is in-memory and
    thread-safe (the store writer + SSE + routes can race on it)."""

    def __init__(self):
        self.rng = random.Random(SEED)
        self._lock = threading.Lock()
        self._seq = 0
        self._events = []            # hook-buffer-shaped
        self._boot = time.time()
        self._build_library()

    # ------------------------------------------------------------ fixtures

    def _mkid(self, kind, n):
        return {"song": "m.s{}", "album": "m.al{}", "artist": "m.ar{}",
                "playlist": "m.pl{}", "video": "m.mv{}"}[kind].format(n)

    def _attributes(self, kind, name, **kw):
        a = {"name": name}
        if kind == "library-songs" or kind == "songs":
            a.update({"artistName": kw.get("artist"),
                      "albumName": kw.get("album"),
                      "durationInMillis": kw.get("duration_ms"),
                      "genreNames": ["Mock"],
                      "trackNumber": kw.get("track_number"),
                      "releaseDate": "2026-01-01",
                      "playParams": {"id": kw.get("catalog_id"),
                                     "kind": "song",
                                     "catalogId": kw.get("catalog_id")},
                      })
            if kw.get("play_count") is not None:
                a["playCount"] = kw["play_count"]
        elif kind.endswith("albums"):
            a.update({"artistName": kw.get("artist"),
                      "trackCount": kw.get("track_count"),
                      "genreNames": ["Mock"], "releaseDate": "2026-01-01"})
        elif kind.endswith("artists"):
            a.update({"genreNames": ["Mock"]})
        elif kind.endswith("playlists"):
            a.update({"trackCount": kw.get("track_count"),
                      "playlistType": kw.get("playlist_type", "USER")})
        return a

    def _song(self, n, artist, album, catalog_id, duration_ms, track_number,
              play_count=0):
        name = "{} {}".format(self.rng.choice(_SONG_WORDS), n)
        return {"id": self._mkid("song", n), "type": "library-songs",
                "attributes": self._attributes(
                    "library-songs", name, artist=artist, album=album,
                    duration_ms=duration_ms, track_number=track_number,
                    catalog_id=catalog_id, play_count=play_count)}

    def _build_library(self):
        rng = self.rng
        self.songs, self.albums, self.artists, self.playlists = \
            [], [], [], []
        self.ratings = {}            # catalog_id -> value (0/1)
        self.favorites = set()       # catalog ids
        cid = 6400000
        lid = 1
        for ai, artist in enumerate(_ARTISTS):
            arid = self._mkid("artist", ai + 1)
            self.artists.append({
                "id": arid, "type": "library-artists",
                "attributes": self._attributes("library-artists", artist),
                "relationships": {}})
            for ti, album in enumerate(rng.sample(_ALBUM_TITLES, 2)):
                alid = self._mkid("album", ai * 2 + ti + 1)
                n_songs = rng.randint(4, 6)
                tracks = []
                for si in range(n_songs):
                    cid += 17
                    lid += 1
                    s = self._song(lid, artist, album, str(cid),
                                   rng.randint(120000, 300000), si + 1,
                                   play_count=rng.randint(0, 30))
                    tracks.append(s)
                self.songs.extend(tracks)
                self.albums.append({
                    "id": alid, "type": "library-albums",
                    "attributes": self._attributes(
                        "library-albums", album, artist=artist,
                        track_count=n_songs),
                    "relationships": {"tracks": {
                        "href": f"/v1/me/library/albums/{alid}/tracks",
                        "data": tracks}}})
        # a couple of user playlists + the made-for-you mixes
        for pi, pname in enumerate(("Mock Favorites", "Deep Focus (mock)")):
            pid = self._mkid("playlist", pi + 1)
            self.playlists.append({
                "id": pid, "type": "library-playlists",
                "attributes": self._attributes(
                    "library-playlists", pname,
                    track_count=min(len(self.songs), 5 + pi * 3)),
                "relationships": {"tracks": {
                    "href": f"/v1/me/library/playlists/{pid}/tracks",
                    "data": self.songs[:5 + pi * 3]}}})
        for mi, mname in enumerate(("Favorites Mix", "New Music Mix")):
            pid = self._mkid("playlist", 10 + mi)
            self.playlists.append({
                "id": pid, "type": "library-playlists",
                "attributes": {**self._attributes(
                    "library-playlists", mname, track_count=3),
                    "playlistType": "M3U_STREAM"},
                "relationships": {"tracks": {
                    "href": f"/v1/me/library/playlists/{pid}/tracks",
                    "data": self.songs[mi * 3:mi * 3 + 3]}}})
        self.catalog_songs = [
            {**s, "type": "songs",
             "id": s["attributes"]["playParams"]["catalogId"]}
            for s in self.songs]
        self.by_library_id = {s["id"]: s for s in self.songs}
        self.by_catalog_id = {s["attributes"]["playParams"]["catalogId"]: s
                              for s in self.songs}
        for p in self.playlists:
            self.by_library_id[p["id"]] = p
        for a in self.albums:
            self.by_library_id[a["id"]] = a
        for a in self.artists:
            self.by_library_id[a["id"]] = a
        # some hearts
        for s in self.catalog_songs[:4]:
            self.favorites.add(s["id"])
        for s in self.catalog_songs[:7]:
            self.ratings[s["id"]] = 1
        # playback: queue = first 5 songs, playing
        self._queue = list(self.catalog_songs[:5])
        self.qi = 0
        self.is_playing = True
        self.volume = 0.7
        # MusicKit's real types: shuffle is a string enum ("songs"|"off"),
        # repeatMode is an int enum — the mock must speak the same types
        # or the response models (rightly) reject it
        self.shuffle = "off"
        self.repeat = 0
        self._track_started = time.time()
        self._push("playbackStateDidChange")

    # ------------------------------------------------------ event buffer

    def _push(self, ev):
        with self._lock:
            self._seq += 1
            cur = self._queue[self.qi] if self._queue else {}
            attrs = cur.get("attributes", {}) or {}
            self._events.append({
                "seq": self._seq, "ev": ev, "ts": int(time.time() * 1000),
                "isPlaying": self.is_playing, "state": 2 if self.is_playing else 0,
                "title": attrs.get("name"), "artist": attrs.get("artistName"),
                "album": attrs.get("albumName"), "id": cur.get("id"),
                "durationMs": attrs.get("durationInMillis"),
                "elapsedMs": self._elapsed_ms(),
                "progress": self._progress(), "volume": self.volume,
                "shuffle": self.shuffle, "repeat": self.repeat,
                "artworkUrl": None})
            if len(self._events) > 300:
                self._events = self._events[-300:]

    def _elapsed_ms(self):
        if not self._queue:
            return 0
        dur = (self._queue[self.qi].get("attributes", {}) or {}).get(
            "durationInMillis") or 180000
        if not self.is_playing:
            return min(self._frozen_ms, dur)
        return min(int((time.time() - self._track_started) * 1000), dur)

    _frozen_ms = 0

    def _progress(self):
        if not self._queue:
            return 0.0
        dur = (self._queue[self.qi].get("attributes", {}) or {}).get(
            "durationInMillis") or 180000
        return self._elapsed_ms() / dur

    def _maybe_advance(self):
        """The synthetic playhead: when a track 'ends', move to the next
        queue item (loops) and emit the change — exactly what the real
        hook buffer sees."""
        if not self._queue:
            return
        dur = (self._queue[self.qi].get("attributes", {}) or {}).get(
            "durationInMillis") or 180000
        if self.is_playing and time.time() - self._track_started >= dur / 1000:
            self.qi = (self.qi + 1) % len(self._queue)   # repeat-all by nature
            self._track_started = time.time()
            self._push("nowPlayingItemDidChange")

    def _tick(self):
        """Progress events ~1/s while playing, like the real hook."""
        if self.is_playing and (not self._events or
                                self._events[-1]["ev"] !=
                                "playbackProgressDidChange" or
                                time.time() - self._events[-1]["ts"] / 1000 >= 1):
            self._push("playbackProgressDidChange")

    # ------------------------------------------------------------ player

    def now_playing(self):
        self._maybe_advance()
        if not self._queue:
            return {"isPlaying": False, "state": 0, "title": None,
                    "artist": None, "album": None, "durationMs": None,
                    "artworkUrl": None, "progress": 0.0, "elapsedMs": 0}
        attrs = self._queue[self.qi].get("attributes", {}) or {}
        return {"isPlaying": self.is_playing,
                "state": 2 if self.is_playing else 0,
                "title": attrs.get("name"),
                "artist": attrs.get("artistName"),
                "album": attrs.get("albumName"),
                "durationMs": attrs.get("durationInMillis"),
                "artworkUrl": None, "progress": self._progress(),
                "elapsedMs": self._elapsed_ms()}

    def playback_settings(self):
        return {"shuffle": self.shuffle, "repeat": self.repeat,
                "volume": self.volume, "isPlaying": self.is_playing}

    def snapshot(self):
        st = self.playback_settings()
        st.update(self.now_playing())
        st["queue"] = self.queue_items()
        return st

    def queue_items(self):
        self._maybe_advance()
        return [{"id": s.get("id"),
                 "title": (s.get("attributes", {}) or {}).get("name"),
                 "artist": (s.get("attributes", {}) or {}).get("artistName"),
                 "kind": s.get("type")} for s in self._queue]

    def queue(self):
        return self.queue_items()

    def play_song(self, catalog_id):
        s = self.by_catalog_id.get(str(catalog_id))
        if not s:
            raise BrowserErrorMock(f"no such catalog song {catalog_id}")
        self._queue = [s]
        self.qi = 0
        self.is_playing = True
        self._track_started = time.time()
        self._push("nowPlayingItemDidChange")

    def play_collection(self, kind, resource_id):
        pool = self.by_library_id.get(str(resource_id))
        tracks = (((pool or {}).get("relationships") or {})
                  .get("tracks", {}).get("data"))
        if not tracks:
            raise BrowserErrorMock(f"no playable tracks for {resource_id}")
        self._queue = list(tracks)
        self.qi = 0
        self.is_playing = True
        self._track_started = time.time()
        self._push("nowPlayingItemDidChange")

    def queue_add(self, catalog_id, play_next=False):
        s = self.by_catalog_id.get(str(catalog_id))
        if not s:
            raise BrowserErrorMock(f"no such catalog song {catalog_id}")
        self._queue.insert(1 if play_next else len(self._queue), s)
        self._push("queueItemsDidChange")

    def queue_reorder(self, ids):
        """Whole-list PUT semantics (#87): the queue becomes EXACTLY this
        order; the playhead stays on the same track (at its new index)."""
        by_id = {s.get("id"): s for s in self._queue}
        missing = [i for i in ids if i not in by_id]
        if missing:
            raise BrowserErrorMock(f"no such queue item(s): {missing[:3]}")
        cur = self._queue[self.qi]["id"] if self._queue else None
        self._queue = [by_id[i] for i in ids]
        self.qi = self._queue.index(by_id[cur]) if cur in by_id else 0
        self._push("queueItemsDidChange")

    def playback_command(self, cmd):
        """Same verb contract as the real layer (routes allow exactly
        play | pause | toggle | next | previous — anything else raises)."""
        if cmd not in ("play", "pause", "toggle", "next", "previous"):
            raise BrowserErrorMock(f"unknown playback command {cmd!r}")
        if cmd == "play":
            self.is_playing = True
            self._track_started = time.time() - self._frozen_ms / 1000
        elif cmd == "pause":
            self._frozen_ms = self._elapsed_ms()
            self.is_playing = False
        elif cmd == "toggle":
            self.playback_command("pause" if self.is_playing else "play")
            return True
        elif cmd == "next":
            self.qi = (self.qi + 1) % max(len(self._queue), 1)
            self._track_started = time.time()
            self._push("nowPlayingItemDidChange")
        elif cmd == "previous":
            self.qi = (self.qi - 1) % max(len(self._queue), 1)
            self._track_started = time.time()
            self._push("nowPlayingItemDidChange")
        self._push("playbackStateDidChange")
        return True

    def playback_property(self, name):
        return getattr(self, name) if name != "isPlaying" else self.is_playing

    def set_playback_property(self, name, value):
        if name == "volume":
            self.volume = float(value)
            self._push("volumeDidChange")
        elif name == "shuffle":
            # route sends "on"|"off"; MusicKit's enum is "songs"|"off"
            self.shuffle = "songs" if value in ("on", "songs", True, 1) \
                else "off"
            self._push("shuffleModeDidChange")
        elif name == "repeat":
            self.repeat = int(value)
            self._push("repeatModeDidChange")

    # ------------------------------------------------------------- stream

    def install_stream_hook(self):
        return True           # the hook is conceptually always installed

    def drain_stream(self, after_seq=0):
        self._maybe_advance()
        self._tick()
        return [e for e in self._events if e["seq"] > after_seq]

    # ------------------------------------------------------------ library

    def _page(self, items, base, q):
        limit = min(int(q.get("limit", ["100"])[0]), 100)
        offset = max(int(q.get("offset", ["0"])[0]), 0)
        page = items[offset:offset + limit]
        out = {"data": page, "href": None}
        if offset + limit < len(items):
            # ABSOLUTE path — paginated() feeds `next` straight back into
            # api_music, so a relative "?offset=..." would not re-match
            nxt = dict(q)
            nxt["offset"] = [str(offset + limit)]
            out["next"] = base + "?" + urllib.parse.urlencode(
                {k: v[0] for k, v in nxt.items()})
        return out

    def _term_match(self, item, term):
        a = item.get("attributes", {}) or {}
        hay = " ".join(str(a.get(k) or "") for k in
                       ("name", "artistName", "albumName")).lower()
        return term.lower() in hay

    def api_music(self, path, timeout=90, fresh=False):
        parsed = urllib.parse.urlsplit(path)
        q = urllib.parse.parse_qs(parsed.query)
        p = parsed.path
        me_lib = "/v1/me/library"

        # ---- library lists ----
        if p in (me_lib, me_lib + "/songs", me_lib + "/albums",
                 me_lib + "/artists", me_lib + "/playlists",
                 me_lib + "/music-videos"):
            kind = p.rsplit("/", 1)[-1] or "songs"
            items = {"songs": self.songs, "albums": self.albums,
                     "artists": self.artists, "playlists": self.playlists,
                     "music-videos": []}.get(kind, self.songs)
            term = (q.get("term") or [None])[0]
            if term:
                items = [i for i in items if self._term_match(i, term)]
            return self._page(items, p, q)

        if p == me_lib + "/recently-added":
            return {"data": list(reversed(self.songs))[:int(
                q.get("limit", ["25"])[0])]}

        if p == me_lib + "/search":
            term = (q.get("term") or [""])[0]
            results = {}
            for kind, pool in (("library-songs", self.songs),
                               ("library-albums", self.albums),
                               ("library-artists", self.artists),
                               ("library-playlists", self.playlists)):
                hits = [i for i in pool if self._term_match(i, term)]
                if hits:
                    results[kind] = {"data": hits[:int(q.get("limit", ["25"])[0])],
                                     "href": None}
            return {"results": results}

        # ---- library detail + relationships ----
        m = re.match(rf"{me_lib}/(songs|albums|artists|playlists|music-videos)"
                     r"/([^/]+)$", p)
        if m:
            item = self.by_library_id.get(m.group(2))
            return {"data": [item] if item else [], "href": None}
        m = re.match(rf"{me_lib}/(songs|albums|artists|playlists|music-videos)"
                     r"/([^/]+)/(tracks|albums|playlists)$", p)
        if m:
            item = self.by_library_id.get(m.group(2))
            rel = ((item or {}).get("relationships") or {}).get(m.group(3)) or {}
            data = rel.get("data", [])
            if m.group(1) == "artists" and m.group(3) == "albums":
                data = [a for a in self.albums
                        if (a["attributes"].get("artistName") ==
                            item["attributes"].get("name"))]
            return self._page(data, p, q)
        # ---- personal ----
        if p == "/v1/me/recommendations":
            groups = []
            for gi, gname in enumerate(("Made for You", "Because You Listened")):
                groups.append({
                    "id": f"m.rec{gi}",
                    "attributes": {"title": {"string": gname},
                                   "reason": "mocked for the demo"},
                    "relationships": {
                        "albums": {"data": self.albums[gi:gi + 2]},
                        "playlists": {"data": self.playlists[gi:gi + 1]}}})
            return {"data": groups}
        if p == "/v1/me/recent/played":
            return {"data": list(reversed(self.songs))[:int(
                q.get("limit", ["20"])[0])]}
        if p == "/v1/me/history/heavy-rotation":
            return {"data": self.catalog_songs[:10],
                    "next": None}

        # ---- catalog ----
        if p == "/v1/catalog/us/search":
            term = (q.get("term") or [""])[0]
            types = (q.get("types") or ["songs"])[0].split(",")
            lim = int(q.get("limit", ["10"])[0])
            pool = {"songs": self.catalog_songs, "albums": self.albums,
                    "artists": self.artists, "playlists": self.playlists}
            results = {}
            for t in types:
                hits = [i for i in pool.get(t, [])
                        if self._term_match(i, term)]
                if hits:
                    results[t] = {"data": hits[:lim], "href": None}
            return {"results": results}
        if p == "/v1/catalog/us/search/suggestions":
            term = (q.get("term") or [""])[0]
            suggestions = []
            for s in self.catalog_songs:
                if self._term_match(s, term):
                    suggestions.append({"content": s})
            return {"results": {"suggestions": suggestions[:5]}}
        if p == "/v1/catalog/us/charts":
            types = (q.get("types") or ["songs"])[0].split(",")
            lim = int(q.get("limit", ["25"])[0])
            results = {t: [{"data": self.catalog_songs[:lim],
                            "name": f"Top {t} (mock)", "chart": t}]
                       for t in types}
            return {"results": results}
        m = re.match(r"/v1/catalog/us/songs/([^/]+)/lyrics$", p)
        if m:
            sid = m.group(1)
            if sid not in self.by_catalog_id:
                raise BrowserErrorMock("404 — no such catalog song")
            return {"data": [{"id": sid, "type": "lyrics",
                              "attributes": {"ttml": self._ttml(sid)}}]}
        m = re.match(r"/v1/catalog/us/(songs|albums|artists|playlists)$", p)
        if m and "ids" in q:
            ids = q["ids"][0].split(",")
            pool = (self.catalog_songs if m.group(1) == "songs"
                    else [dict(x, type=m.group(1))
                          for x in (self.albums if m.group(1) == "albums"
                                    else self.artists if m.group(1) == "artists"
                                    else self.playlists)])
            key = "id"
            hits = [i for i in pool if i.get(key) in ids]
            return {"data": hits, "href": None}
        m = re.match(r"/v1/catalog/us/(songs|albums|artists|playlists)"
                     r"/([^/]+)$", p)
        if m:
            item = self.by_catalog_id.get(m.group(2))
            return {"data": [item] if item else [], "href": None}
        m = re.match(r"/v1/catalog/us/(albums|playlists|artists)"
                     r"/([^/]+)/(tracks|playlists)$", p)
        if m:
            item = self.by_catalog_id.get(m.group(2))
            rel = ((item or {}).get("relationships") or {}).get(m.group(3)) or {}
            return self._page(rel.get("data", []), p, q)

        # ratings reads (get_rating rides raw_api, but be lenient here too)
        m = re.match(r"/v1/me/ratings/songs/([^/]+)$", p)
        if m:
            v = self.ratings.get(m.group(1), 0)
            return {"data": [{"id": m.group(1), "type": "ratings",
                              "attributes": {"value": v}}] if v else []}

        raise BrowserErrorMock(f"mock has no fixture for {path.split('?')[0]}")

    def raw_api(self, path, method="GET", body=None, timeout=60, fresh=False):
        parsed = urllib.parse.urlsplit(path)
        q = urllib.parse.parse_qs(parsed.query)
        p = parsed.path

        # ratings
        m = re.match(r"/v1/me/ratings/songs/([^/]+)$", p)
        if m and method == "GET":
            v = self.ratings.get(m.group(1), 0)
            return {"data": [{"id": m.group(1), "type": "ratings",
                              "attributes": {"value": v}}] if v else []}
        if m and method == "PUT":
            self.ratings[m.group(1)] = 1
            self._push("ratingDidChange")
            return {}
        if m and method == "DELETE":
            self.ratings[m.group(1)] = 0
            return {}

        # favorites
        if p == "/v1/me/favorites":
            ids = (q.get("ids[songs]") or q.get("ids[library-songs]") or
                   [""])[0].split(",")
            if method == "POST":
                self.favorites.update(i for i in ids if i)
            elif method == "DELETE":
                self.favorites.difference_update(ids)
            return {}

        # library add/remove (songs + albums)
        if p == "/v1/me/library" and method == "POST":
            for key in ("ids[songs]", "ids[albums]"):
                for cid in (q.get(key) or [""])[0].split(","):
                    item = self.by_catalog_id.get(cid)
                    if item and key == "ids[songs]" and item not in self.songs:
                        self.songs.append(item)
            self._push("libraryDidChange")
            return {"status": 202}
        m = re.match(r"/v1/me/library/songs/([^/]+)$", p)
        if m and method == "DELETE":
            self.songs = [s for s in self.songs if s["id"] != m.group(1)]
            self._push("libraryDidChange")
            return {"status": 202}
        m = re.match(r"/v1/me/library/albums/([^/]+)$", p)
        if m and method == "DELETE":
            self.albums = [a for a in self.albums if a["id"] != m.group(1)]
            return {"status": 202}

        # playlist CRUD
        if p == me_lib_playlist_path() and method == "POST":
            name = ((body or {}).get("attributes") or {}).get("name") or ""
            pid = self._mkid("playlist", len(self.playlists) + 100)
            self.playlists.append({
                "id": pid, "type": "library-playlists",
                "attributes": self._attributes("library-playlists", name,
                                               track_count=0),
                "relationships": {"tracks": {"data": []}}})
            self.by_library_id[pid] = self.playlists[-1]
            return {"data": [self.playlists[-1]]}
        m = re.match(rf"{me_lib_playlist_path()}/([^/]+)$", p)
        if m and method == "PATCH":
            pl = self.by_library_id.get(m.group(1))
            if not pl:
                raise BrowserErrorMock("404 — no such playlist")
            attrs = (body or {}).get("attributes") or {}
            if "name" in attrs:
                pl["attributes"]["name"] = attrs["name"]
            return {}
        if m and method == "DELETE":
            pl = self.by_library_id.get(m.group(1))
            if pl:
                # the documented husk quirk: a deleted playlist reads back
                # with name=None until Apple's async apply finishes
                pl["attributes"]["name"] = None
                pl["_deleted"] = True
            return {"status": 204}
        m = re.match(rf"{me_lib_playlist_path()}/([^/]+)/tracks$", p)
        if m:
            pl = self.by_library_id.get(m.group(1))
            if not pl:
                raise BrowserErrorMock("404 — no such playlist")
            rel = pl["relationships"]["tracks"]
            if method == "POST":
                cids = (q.get("ids[songs]") or
                        (body or {}).get("ids", {}).get("songs") or [""])
                added = [self.by_catalog_id[c] for c in cids[0].split(",")
                         if c in self.by_catalog_id]
                rel["data"] = rel.get("data", []) + added
                self._push("queueItemsDidChange")
                return {"status": 202}
            if method == "PUT":
                lids = ((body or {}).get("ids") or
                        [{}]).get("library-songs") or []
                ordered = [self.by_library_id[i] for i in lids
                           if i in self.by_library_id]
                rel["data"] = ordered
                return {"status": 202}
        raise BrowserErrorMock(
            f"mock has no write fixture for {method} {p}")

    # ------------------------------------------------------------- lyrics

    def _ttml(self, song_id):
        """Deterministic synced-lyrics TTML — same lines every boot.
        The <p> tags are UNPREFIXED on purpose: Apple's real documents put
        begin/end on plain <p> elements, and the production parser keys on
        `<p ... begin=` — a mock fixture must parse with the real code."""
        lines = []
        t = 0.0
        for i in range(14):
            text = _LYRIC_LINES[i % len(_LYRIC_LINES)]
            lines.append(f'<p begin="{t:.3f}s" end="{t + 3.2:.3f}s">'
                         f"{text}</p>")
            t += 3.2
        return ('<tt:tt xmlns:tt="http://www.w3.org/ns/ttml">'
                "<tt:body><tt:div>" + "".join(lines) +
                "</tt:div></tt:body></tt:tt>")

    # ------------------------------------------------- favorites playlist

    def find_library_playlist(self, name, fresh=False):
        for p in self.playlists:
            if ((p.get("attributes") or {}).get("name") or "").lower() == \
                    (name or "").lower() and not p.get("_deleted"):
                return p["id"]
        return None

    def playlist_tracks(self, playlist_id, fresh=False):
        pl = self.by_library_id.get(playlist_id)
        if not pl:
            return []
        return [dict(s) for s in
                pl["relationships"]["tracks"].get("data", [])]


def me_lib_playlist_path():
    return "/v1/me/library/playlists"


class BrowserErrorMock(BrowserError):
    """Raised where the real layer would raise BrowserError — it IS one,
    so every route's except-clause works unchanged (502 envelope, or 404
    when the detail says 404)."""


# ---------------------------------------------------------------- wiring
# mock.py must NOT import musickit (cycle). install() receives the module.

def install(mk_module):
    """Swap the musickit surface for the mock. Same BrowserError type so
    every route's except-clause keeps working."""
    mock = MockKit()

    mk_module.api_music = mock.api_music
    mk_module.raw_api = mock.raw_api
    mk_module.paginated = _mock_paginated(mock)
    # NOTE: song_row/item_row stay REAL — they are pure dict->dict
    # normalizers, and the mock's point is to exercise them (a mock that
    # bypassed normalization would test nothing)
    mk_module.playlist_tracks = mock.playlist_tracks
    mk_module.find_library_playlist = mock.find_library_playlist
    mk_module.set_favorite = _mock_set_favorite(mock)
    mk_module.rate_song = _mock_rate_song(mock)
    mk_module.get_rating = _mock_get_rating(mock)
    mk_module.library_add = _mock_library_add(mock)
    mk_module.library_remove = _mock_library_remove(mock)
    mk_module.library_add_albums = _mock_library_add_albums(mock)
    mk_module.library_remove_album = _mock_library_remove_album(mock)
    mk_module.playlist_create = _mock_playlist_create(mock)
    mk_module.playlist_add_tracks = _mock_playlist_add_tracks(mock)
    mk_module.playlist_set_tracks = _mock_playlist_set_tracks(mock)
    mk_module.playlist_rename = _mock_playlist_rename(mock)
    mk_module.playlist_delete = _mock_playlist_delete(mock)
    mk_module.queue_add = mock.queue_add
    mk_module.queue_reorder = mock.queue_reorder
    mk_module.playback_command = mock.playback_command
    mk_module.now_playing = mock.now_playing
    mk_module.install_stream_hook = mock.install_stream_hook
    mk_module.drain_stream = mock.drain_stream
    mk_module.snapshot = mock.snapshot
    mk_module.play_song = mock.play_song
    mk_module.queue = mock.queue
    mk_module.playback_property = mock.playback_property
    mk_module.set_playback_property = mock.set_playback_property
    mk_module.playback_settings = mock.playback_settings
    mk_module.play_collection = mock.play_collection
    return mock


def _mock_paginated(mock):
    def paginated(first_path, extract, fresh=False):
        out, url = [], first_path
        while url:
            data = mock.api_music(url)
            out.extend(extract(data))
            url = data.get("next")
        return out
    return paginated


# normalizers: the real ones are reused (see install()) — nothing to wrap


def _mock_set_favorite(mock):
    def set_favorite(kind, resource_id, favorited):
        mock.raw_api(f"/v1/me/favorites?ids[{kind}]={resource_id}",
                     method="POST" if favorited else "DELETE")
        return True
    return set_favorite


def _mock_rate_song(mock):
    def rate_song(song_id, like):
        mock.raw_api(f"/v1/me/ratings/songs/{song_id}",
                     method="PUT" if like else "DELETE")
        return True
    return rate_song


def _mock_get_rating(mock):
    def get_rating(song_id, fresh=False):
        data = mock.raw_api(f"/v1/me/ratings/songs/{song_id}")
        rows = data.get("data", [])
        return rows[0].get("attributes", {}).get("value") if rows else 0
    return get_rating


def _mock_library_add(mock):
    def library_add(catalog_ids):
        ids = ",".join(str(i) for i in catalog_ids)
        return mock.raw_api(f"/v1/me/library?ids[songs]={ids}", method="POST")
    return library_add


def _mock_library_remove(mock):
    def library_remove(library_song_ids):
        for lid in library_song_ids:
            mock.raw_api(f"/v1/me/library/songs/{lid}", method="DELETE")
        return True
    return library_remove


def _mock_library_add_albums(mock):
    def library_add_albums(catalog_album_ids):
        ids = ",".join(str(i) for i in catalog_album_ids)
        return mock.raw_api(f"/v1/me/library?ids[albums]={ids}", method="POST")
    return library_add_albums


def _mock_library_remove_album(mock):
    def library_remove_album(library_album_id):
        return mock.raw_api(f"/v1/me/library/albums/{library_album_id}",
                            method="DELETE")
    return library_remove_album


def _mock_playlist_create(mock):
    def playlist_create(name, description=""):
        data = mock.raw_api(me_lib_playlist_path(), method="POST",
                            body={"attributes": {"name": name,
                                                 "description": description}})
        return data["data"][0]["id"]
    return playlist_create


def _mock_playlist_add_tracks(mock):
    def playlist_add_tracks(playlist_id, catalog_ids):
        ids = ",".join(str(i) for i in catalog_ids)
        return mock.raw_api(
            f"{me_lib_playlist_path()}/{playlist_id}/tracks?ids[songs]={ids}",
            method="POST")
    return playlist_add_tracks


def _mock_playlist_set_tracks(mock):
    def playlist_set_tracks(playlist_id, library_ids):
        return mock.raw_api(
            f"{me_lib_playlist_path()}/{playlist_id}/tracks",
            method="PUT", body={"ids": {"library-songs": list(library_ids)}})
    return playlist_set_tracks


def _mock_playlist_rename(mock):
    def playlist_rename(playlist_id, name=None, description=None):
        attrs = {k: v for k, v in (("name", name),
                                   ("description", description)) if v}
        return mock.raw_api(f"{me_lib_playlist_path()}/{playlist_id}",
                            method="PATCH", body={"attributes": attrs})
    return playlist_rename


def _mock_playlist_delete(mock):
    def playlist_delete(playlist_id):
        return mock.raw_api(f"{me_lib_playlist_path()}/{playlist_id}",
                            method="DELETE")
    return playlist_delete
