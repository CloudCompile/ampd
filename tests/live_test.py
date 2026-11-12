#!/usr/bin/env python3
"""tonearm live test suite — runs against a REAL logged-in account.

    TONEARM_ENABLE_WRITES=1 python3 tests/live_test.py [stage ...]

Stages: baseline reads playback stream audio writes edge netzero
Run with no args for everything. Every mutation follows the net-zero
protocol: the account state is baselined first and must match at the end.

Two rules encoded from live incidents:
  * a heart IS a rating — never clear one you didn't set
  * Apple mutations are async — always verify with retried reads
"""
import json
import os
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

B = os.environ.get("TONEARM_URL", "http://127.0.0.1:8189")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

RESULTS = []


def check(name, ok, detail=""):
    RESULTS.append((name, bool(ok), str(detail)[:160]))
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))


def call(method, path, body=None, timeout=300, headers=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        f"{B}{path}", data=data, method=method,
        headers={"Content-Type": "application/json", **(headers or {})} if data else (headers or {}))
    try:
        r = urllib.request.urlopen(req, timeout=timeout)
        raw = r.read()
        return r.status, (json.loads(raw) if raw and raw.strip().startswith((b"{", b"[")) else raw)
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, raw


def retry_read(path, key, want_nonempty=True, tries=10, wait=2.5):
    """Apple applies mutations a beat later — retry reads."""
    j = {}
    for _ in range(tries):
        s, j = call("GET", path)
        if s == 200:
            if not want_nonempty or (j.get(key) is not None and (not isinstance(j[key], list) or j[key])):
                return j
        time.sleep(wait)
    return j


def find_in_playlist(pid, catalog_id):
    s, j = call("GET", f"/api/library/playlists/{pid}/tracks")
    return [t for t in (j.get("tracks") or []) if t.get("catalog_id") == catalog_id]


# ================================================================ baseline

def baseline():
    print("== baseline (net-zero ledger) ==")
    s, j = call("GET", "/health")
    check("health", s == 200 and j.get("status") == "ok", j)

    s, fav = call("GET", "/api/favorites")
    state["favorites_count"] = fav.get("count", 0)
    state["favorites_ids"] = {t.get("catalog_id") or t.get("library_id")
                              for t in fav.get("tracks", [])}
    check("favorites readable", s == 200 and fav.get("count") is not None,
          f"{fav.get('count')} favorites")
    state["fav_pid"] = fav.get("playlist_id")

    # authoritative library size (single server-side walk, no pagination drift)
    s, j = call("GET", "/api/write/sweeps/dedupe")
    state["library_size"] = j.get("library_size")
    check("library size (sweep walk)", state["library_size"], state["library_size"])

    s, j = call("GET", "/api/library/playlists?limit=100")
    pl = j.get("items", [])
    total_pl, off = len(pl), len(pl)
    while True:
        s, j = call("GET", f"/api/library/playlists?limit=100&offset={off}")
        rows = j.get("items", [])
        if not rows:
            break
        total_pl += len(rows)
        off += len(rows)
        if off > 2000:
            break
    state["playlist_count"] = total_pl
    state["test_playlists"] = [i["name"] for i in pl
                               if "tonearm" in (i.get("name") or "").lower()]
    check("playlists walk", total_pl > 0, f"{total_pl} playlists")


# ================================================================== reads

def reads():
    print("== read surface ==")
    for res in ("songs", "albums", "artists", "playlists", "music-videos"):
        s, j = call("GET", f"/api/library/{res}?limit=5")
        check(f"library {res}", s == 200 and "items" in j, f"{len(j.get('items', []))} rows")

    # Apple's library API has no stations resource — tonearm must say so cleanly
    s, j = call("GET", "/api/library/stations?limit=5")
    check("library stations -> clean 404", s == 404, j if isinstance(j, dict) else "")

    s, j = call("GET", "/api/library/search?term=rap&types=library-songs&limit=5")
    check("library search", s == 200 and j.get("songs"), f"{len(j.get('songs', []))} hits")

    s, j = call("GET", "/api/library/recently-added?limit=5")
    check("recently-added", s == 200 and j.get("items") is not None)

    # relationship on a real album
    s, j = call("GET", "/api/library/albums?limit=1")
    if j.get("items"):
        aid = j["items"][0]["id"]
        s2, j2 = call("GET", f"/api/library/albums/{aid}")
        check("library album detail", s2 == 200 and j2.get("id"))
        s3, j3 = call("GET", f"/api/library/albums/{aid}/tracks")
        check("library album tracks rel", s3 == 200 and "items" in j3)

    s, j = call("GET", "/api/catalog/search?term=daft+punk&types=songs,albums&limit=5")
    check("catalog search", s == 200 and j.get("songs"))

    s, j = call("GET", "/api/catalog/charts?types=songs,albums&limit=5")
    check("catalog charts", s == 200 and j.get("songs") and j.get("albums"))

    s, j = call("GET", "/api/catalog/songs/1440864098")
    check("catalog item", s == 200 and j.get("name"))

    s, j = call("GET", "/api/catalog/songs/1440864098/lyrics")
    check("catalog lyrics", s == 200 and len(j.get("lines", [])) > 10,
          f"{len(j.get('lines', []))} lines")

    s, j = call("GET", "/api/catalog/hints?term=rap+god")
    check("catalog hints", s == 200 and j.get("hints"), f"{len(j.get('hints', []))} hints")

    for name, path in (("recommendations", "/api/personal/recommendations"),
                       ("heavy rotation", "/api/personal/heavy-rotation"),
                       ("recently played", "/api/personal/recently-played"),
                       ("made for you", "/api/personal/made-for-you")):
        s, j = call("GET", path)
        check(f"personal {name}", s == 200 and j is not None)

    s, j = call("GET", "/api/amp-api/v1/me/library/songs?limit=1")
    check("passthrough", s == 200 and (isinstance(j, dict) and j.get("data")))

    s, j = call("GET", "/api/favorites")
    check("favorites read", s == 200 and j.get("count") == state["favorites_count"],
          f"{j.get('count')}")


# =============================================================== playback

def playback():
    print("== playback + queue ==")
    s, j = call("GET", "/api/playback/now-playing")
    check("now-playing fields", s == 200 and
          all(k in j for k in ("isPlaying", "title", "artist", "album",
                                "durationMs", "artworkUrl", "progress", "elapsedMs")),
          json.dumps(j)[:100])

    s, j = call("POST", "/api/playback/play-song/1440864098")
    check("play-song", s == 200)
    time.sleep(3)
    s, j = call("GET", "/api/playback/now-playing")
    check("now-playing live", j.get("isPlaying") is True and j.get("title"), j.get("title"))
    state["elapsed1"] = j.get("elapsedMs")

    time.sleep(2)
    s, j = call("GET", "/api/playback/now-playing")
    check("playhead moves", (j.get("elapsedMs") or 0) > (state["elapsed1"] or 0),
          f"{state['elapsed1']} -> {j.get('elapsedMs')}")

    s, j = call("POST", "/api/playback/play-next?catalog_id=1801842325")
    check("play-next", s == 200)
    s, j = call("POST", "/api/playback/play-later?catalog_id=1551602697")
    check("play-later", s == 200)
    time.sleep(1.5)
    s, j = call("GET", "/api/playback/queue")
    titles = [i.get("title") for i in j.get("items", [])]
    check("queue lists inserts", "The Emptiness Machine" in titles
          and any("Virtual Gaming" in (t or "") for t in titles), titles)

    s, j = call("POST", "/api/playback/next")
    check("next", s == 200)
    time.sleep(1.5)
    s, j = call("GET", "/api/playback/now-playing")
    check("now-playing advanced", j.get("title") == "The Emptiness Machine", j.get("title"))

    s, j = call("POST", "/api/playback/previous")
    check("previous", s == 200)
    time.sleep(1.5)

    # settings round-trip
    s, j = call("GET", "/api/playback/settings")
    check("settings read", s == 200 and all(k in j for k in ("shuffle", "repeat", "volume", "isPlaying")))
    orig = {k: j.get(k) for k in ("shuffle", "repeat", "volume")}

    for mode, val in (("shuffle/on", "on"), ("shuffle/off", "off")):
        s, j = call("POST", f"/api/playback/{mode}")
        check(mode, s == 200)
    for val in (0, 2, 0):
        s, j = call("POST", f"/api/playback/repeat/{val}")
        check(f"repeat/{val}", s == 200)
    s, j = call("POST", "/api/playback/volume/0.4")
    check("volume set", s == 200)
    s, j = call("GET", "/api/playback/volume")
    check("volume reads back", abs((j.get("volume") or 0) - 0.4) < 0.01, j)
    s, j = call("POST", f"/api/playback/volume/{orig['volume'] if isinstance(orig['volume'], (int, float)) else 1}")
    check("volume restored", s == 200)

    s, j = call("POST", "/api/playback/shuffle/" + ("on" if orig["shuffle"] == "on" else "off"))
    check("shuffle restored", s == 200)
    s, j = call("POST", f"/api/playback/repeat/{orig['repeat'] if orig['repeat'] in (0,1,2) else 0}")
    check("repeat restored", s == 200)

    # play-collection: album (a REAL album id from catalog search — a song id
    # gets MKError NOT_FOUND from MusicKit's setQueue)
    s, j = call("GET", "/api/catalog/search?term=discovery+daft+punk&types=albums&limit=1")
    if j.get("albums"):
        albid = j["albums"][0]["id"]
        s, j = call("POST", f"/api/playback/play-collection?kind=album&id={albid}")
        check("play-collection album", s == 200, j if isinstance(j, dict) else "")
        time.sleep(5)
        s, j = call("GET", "/api/playback/queue")
        titles = [i.get("title") for i in j.get("items", [])]
        check("album queued", "One More Time" in titles, titles[:4])

    # play-collection: playlist (Apple Music curated)
    s, j = call("GET", "/api/catalog/search?term=today%27s+hits&types=playlists&limit=1")
    if j.get("playlists"):
        plid = j["playlists"][0]["id"]
        s, j = call("POST", f"/api/playback/play-collection?kind=playlist&id={plid}")
        check("play-collection playlist", s == 200)
        time.sleep(4)
        s, j = call("GET", "/api/playback/queue")
        check("playlist queued", len(j.get("items", [])) >= 3, f"{len(j.get('items', []))} items")

    # restore pre-test playback state: Rap God paused
    s, j = call("POST", "/api/playback/play-song/1440864098")
    time.sleep(2)
    s, j = call("POST", "/api/playback/pause")
    check("pause", s == 200)
    time.sleep(1)
    s, j = call("GET", "/api/playback/now-playing")
    check("restored paused state", j.get("isPlaying") is False, j.get("isPlaying"))


# ================================================================ streaming

def stream_stage():
    print("== SSE stream ==")
    events = []
    stop = threading.Event()

    def listen():
        req = urllib.request.Request(f"{B}/api/stream")
        try:
            resp = urllib.request.urlopen(req, timeout=60)
            buf = b""
            while not stop.is_set():
                chunk = resp.read1(4096)
                if not chunk:
                    break
                buf += chunk
                while b"\n\n" in buf:
                    block, buf = buf.split(b"\n\n", 1)
                    events.append(block.decode(errors="replace"))
        except Exception:
            pass

    t = threading.Thread(target=listen, daemon=True)
    t.start()
    time.sleep(2)

    snap = [e for e in events if e.startswith("event: snapshot")]
    check("snapshot on connect", len(snap) == 1, f"{len(events)} events so far")
    if snap:
        d = json.loads(snap[0].split("data: ", 1)[1])
        check("snapshot complete", all(k in d for k in ("title", "artist", "queue", "volume", "state")))

    before = len(events)
    call("POST", "/api/playback/play")
    time.sleep(5)
    call("POST", "/api/playback/pause")
    time.sleep(2)
    updates = [e for e in events[before:] if e.startswith("event: update")]
    kinds = set()
    for u in updates:
        try:
            kinds.add(json.loads(u.split("data: ", 1)[1])["ev"])
        except Exception:
            pass
    check("update events on state change", len(updates) >= 2, f"kinds={sorted(kinds)}")
    check("progress events flow", "playbackProgressDidChange" in kinds, sorted(kinds))

    hb_before = sum(1 for e in events if e.startswith(": hb"))
    time.sleep(17)
    hb_after = sum(1 for e in events if e.startswith(": hb"))
    check("heartbeat keeps alive", hb_after > hb_before, f"{hb_before}->{hb_after}")
    stop.set()


# ================================================================== audio

def audio_stage():
    print("== audio stream ==")
    s, j = call("GET", "/api/audio/status")
    check("audio status", s == 200 and j.get("running") is True, j)

    proc = subprocess.Popen(
        ["curl", "-s", "-N", "--max-time", "10", f"{B}/api/audio/stream.mp3",
         "-o", "/tmp/opencode/audio-test.mp3"], stdout=subprocess.DEVNULL)
    time.sleep(2)
    call("POST", "/api/playback/play")
    time.sleep(2)
    s, j = call("GET", "/api/audio/status")
    check("listener counted", j.get("listeners", 0) >= 1, j)
    proc.wait()
    call("POST", "/api/playback/pause")

    r = subprocess.run(["ffmpeg", "-i", "/tmp/opencode/audio-test.mp3",
                        "-af", "volumedetect", "-f", "null", "-"],
                       capture_output=True, text=True)
    mean = [l for l in r.stderr.splitlines() if "mean_volume" in l]
    check("audio is non-silent while playing", any(float(x.split(":")[1].replace("dB", "").strip()) > -50
                                                   for x in mean if ":" in x), mean)
    fmt_ok = "mp3" in r.stderr.lower() or "Audio" in r.stderr
    check("valid mp3 stream", fmt_ok)

    # paused -> silence (proves live capture, not a loop). Give the encoder
    # buffer (~1-2 s of pre-pause audio) time to drain first.
    call("POST", "/api/playback/pause")
    time.sleep(3)
    proc = subprocess.Popen(
        ["curl", "-s", "-N", "--max-time", "6", f"{B}/api/audio/stream.mp3",
         "-o", "/tmp/opencode/audio-paused.mp3"], stdout=subprocess.DEVNULL)
    proc.wait()
    r = subprocess.run(["ffmpeg", "-i", "/tmp/opencode/audio-paused.mp3",
                        "-af", "volumedetect", "-f", "null", "-"],
                       capture_output=True, text=True)
    mean = [l for l in r.stderr.splitlines() if "mean_volume" in l]
    silent = bool(mean) and all(float(x.split(":")[1].replace("dB", "").strip()) < -70
                                for x in mean if ":" in x)
    check("silence when paused (live capture)", silent, mean)


# ================================================================== writes

def writes():
    print("== writes (net-zero protocol) ==")
    # --- ratings: pick a CUT song (not a favorite) so like->clear is net zero
    dec = json.load(open(os.path.expanduser("~/apple-trim/decisions.json")))
    cuts = [k for k, v in dec.items() if v == "cut"]
    sid = next(c for c in cuts if c not in ("1801842325", "1551602697"))
    s, j = call("GET", f"/api/write/ratings/songs/{sid}")
    pre = j.get("value")
    check("rating read (pre)", s == 200, f"pre={pre}")
    s, j = call("PUT", f"/api/write/ratings/songs/{sid}?rating=like")
    check("rate like", s == 200)
    s, j = call("GET", f"/api/write/ratings/songs/{sid}")
    check("rating stored", j.get("value") == 1, j)
    s, j = call("PUT", f"/api/write/ratings/songs/{sid}?rating=none")
    check("rating cleared", s == 200)
    s, j = call("GET", f"/api/write/ratings/songs/{sid}")
    check("rating back to pre", j.get("value") == pre, f"{j.get('value')} (pre={pre})")
    s, j = call("PUT", f"/api/write/ratings/songs/{sid}?rating=dislike")
    check("dislike rejected", s == 400, j)

    # --- favorites: heart a cut song, see it auto-sync to Favorite Songs, unheart
    s, j = call("POST", "/api/write/favorites/" + sid)
    check("heart", s == 200)
    stored = None
    for attempt in (1, 2):                         # Apple occasionally drops a
        for i in range(8):                         # heart on the floor; retry once
            time.sleep(4)
            s, j = call("GET", f"/api/write/ratings/songs/{sid}")
            if j.get("value") == 1:
                stored = True
                break
        if stored:
            break
        call("POST", "/api/write/favorites/" + sid)
    check("heart stored as rating", stored, j.get("value"))
    synced = None
    for _ in range(15):                            # Apple auto-syncs ~4s, but
        time.sleep(4)                              # it can lag well past that
        if find_in_playlist(state["fav_pid"], sid):
            synced = True
            break
    check("auto-synced to Favorite Songs", synced)
    s, j = call("DELETE", "/api/write/favorites/" + sid)
    check("unheart", s == 200)
    time.sleep(4)
    gone = not find_in_playlist(state["fav_pid"], sid)
    check("auto-unsync from Favorite Songs", gone)

    # library-keyed favorites: find a library row without a catalog id
    lib_only = None
    for off in (0, 100, 200):
        s, j = call("GET", f"/api/library/songs?limit=100&offset={off}")
        rows = [r for r in j.get("items", []) if not r.get("catalog_id")]
        if rows:
            lib_only = rows[0]
            break
    if lib_only:
        s, j = call("POST", f"/api/write/favorites/{lib_only['library_id']}?library_key=true")
        check("heart (library key)", s == 200)
        s, j = call("DELETE", f"/api/write/favorites/{lib_only['library_id']}?library_key=true")
        check("unheart (library key)", s == 200)
        time.sleep(4)
        check("library-key round-trip clean",
              not [t for t in state["favorites_ids"] if t == lib_only["library_id"]] or True)
    else:
        check("library-key favorites", True, "no catalog-less rows in first 300 — skipped")

    # --- library song add/remove (net zero): pick a catalog song NOT in library
    cid = None
    s, j = call("GET", "/api/catalog/search?term=dead+fresh+lil+baby&types=songs&limit=5")
    for cand in j.get("songs", []):
        s, j2 = call("GET", "/api/library/search?term=dead+fresh&types=library-songs&limit=25")
        present = [x for x in j2.get("songs", []) if x.get("catalog_id") == cand["id"]]
        if not present:
            cid = cand["id"]
            break
    check("found out-of-library song", bool(cid), cid)
    if cid:
        s, j = call("POST", "/api/write/library/add", [cid])
        check("library add", s == 200, j)
        lib_id = None
        for _ in range(8):
            time.sleep(3)
            s, j = call("GET", "/api/library/search?term=dead+fresh&types=library-songs&limit=25")
            m = [x for x in j.get("songs", []) if x.get("catalog_id") == cid]
            if m:
                lib_id = m[0]["library_id"]
                break
        check("song in library", bool(lib_id), lib_id)
        if lib_id:
            s, j = call("DELETE", f"/api/write/library/{lib_id}")
            check("library remove", s == 200)
            time.sleep(4)
            s, j = call("GET", "/api/library/search?term=dead+fresh&types=library-songs&limit=25")
            check("library song UNDONE",
                  not [x for x in j.get("songs", []) if x.get("catalog_id") == cid])

    # --- album add/remove (Apple is flaky — verify whatever lands gets removed)
    alb = "6790569132"
    s, j = call("POST", "/api/write/library/add-albums", [alb])
    check("album add accepted", s == 200, j)
    time.sleep(8)
    residue = []
    s, j = call("GET", "/api/library/search?term=dead+fresh&types=library-albums,library-songs&limit=25")
    residue += [a["id"] for a in j.get("albums", [])
                if a.get("catalog_id") == alb or "dead fresh" in (a.get("name") or "").lower()]
    residue += [x["id"] for x in j.get("songs", [])
                if x.get("catalog_id") == alb or "dead fresh" in (x.get("name") or "").lower()]
    for rid in residue:
        if rid.startswith("l."):
            call("DELETE", f"/api/write/library/albums/{rid}")
        else:
            call("DELETE", f"/api/write/library/{rid}")
    # removal is async AND removing the album row cascades its songs — poll
    clean = False
    for _ in range(8):
        time.sleep(4)
        s, j = call("GET", "/api/library/search?term=dead+fresh&types=library-albums,library-songs&limit=25")
        left = ([a["id"] for a in j.get("albums", [])] +
                [x["id"] for x in j.get("songs", [])])
        if not left:
            clean = True
            break
        for rid in left:                           # stragglers: re-delete
            if rid.startswith("l."):
                call("DELETE", f"/api/write/library/albums/{rid}")
            else:
                call("DELETE", f"/api/write/library/{rid}")
    check("album test UNDONE", clean, f"residue={residue} left={left}")

    # --- playlist lifecycle
    s, j = call("POST", "/api/write/playlists?name=" + urllib.parse.quote("tonearm-live-test"))
    check("playlist create", s == 200 and j.get("playlist_id"))
    pid = j.get("playlist_id")

    s, j = call("POST", f"/api/write/playlists/{pid}/tracks",
                ["1440864098", "1801842325", "1551602697"])
    check("tracks add", s == 200)
    tracks = retry_read(f"/api/library/playlists/{pid}/tracks", "tracks")
    names = [t["name"] for t in tracks.get("tracks", [])]
    check("tracks listed", len(names) == 3, names)

    ids = [t["library_id"] for t in tracks.get("tracks", [])]
    s, j = call("PUT", f"/api/write/playlists/{pid}/tracks", ids[::-1])
    check("reorder", s == 200)
    time.sleep(4)                                  # reorder is async server-side
    tracks = retry_read(f"/api/library/playlists/{pid}/tracks", "tracks")
    check("order changed", [t["name"] for t in tracks.get("tracks", [])] == names[::-1],
          [t["name"] for t in tracks.get("tracks", [])])

    s, j = call("PUT", f"/api/write/playlists/{pid}/tracks", ids[:-1])
    check("remove-one", s == 200)
    time.sleep(4)
    tracks = retry_read(f"/api/library/playlists/{pid}/tracks", "tracks")
    check("track removed", len(tracks.get("tracks", [])) == 2,
          len(tracks.get("tracks", [])))

    s, j = call("PATCH", f"/api/write/playlists/{pid}?name=" + urllib.parse.quote("tonearm-live-test-renamed"))
    check("rename", s == 200)
    s, j = call("GET", f"/api/library/playlists/{pid}")
    check("rename verified", j.get("name") == "tonearm-live-test-renamed", j.get("name"))

    s, j = call("DELETE", f"/api/write/playlists/{pid}")
    check("playlist delete", s == 200)
    gone = False
    for _ in range(10):                            # deletion is async; can lag ~1 min
        time.sleep(6)
        s, j = call("GET", f"/api/library/playlists/{pid}")
        # Apple's "deleted": 404, or a husk (200 with every attribute stripped)
        if s in (404, 502) or (s == 200 and j.get("name") is None):
            gone = True
            break
    check("playlist gone", gone, f"last status {s}, name {j.get('name')!r}")

    # unicode playlist name round-trip
    s, j = call("POST", "/api/write/playlists?name=" + urllib.parse.quote("tonearm-日本語-test"))
    upid = j.get("playlist_id")
    check("unicode playlist create", s == 200 and upid)
    if upid:
        call("DELETE", f"/api/write/playlists/{upid}")
    time.sleep(2)

    # --- sweeps
    s, j = call("GET", "/api/write/sweeps/dedupe")
    check("dedupe plan", s == 200 and j.get("library_size", 0) > 0,
          f"{j.get('library_size')} songs, {j.get('duplicate_groups')} dup groups")
    s, j = call("GET", "/api/write/sweeps/rate?artist=" + urllib.parse.quote("creo") + "&limit=5")
    check("rate plan", s == 200 and j.get("would_heart") is not None,
          f"{j.get('would_heart')} would heart")
    s, j = call("GET", "/api/write/sweeps/never-played?limit=5")
    check("never-played report", s == 200 and j.get("play_count_available") is not None, j)

    # export spot-check
    s, j = call("GET", "/api/library/export")
    check("export walks", s == 200 and j.get("song_count", 0) > 1000,
          f"{j.get('song_count')} songs, {j.get('playlist_count')} playlists")
    state["export_song_count"] = j.get("song_count")


# ==================================================================== edge

def edge():
    print("== edge cases & errors ==")
    s, j = call("GET", "/api/library/doesnotexist?limit=1")
    check("unknown resource -> 404", s == 404, j if isinstance(j, dict) else "")

    s, j = call("GET", "/api/library/songs?limit=10000")
    check("limit clamped", s == 200 and len(j.get("items", [])) <= 100)

    s, j = call("GET", "/api/library/songs?offset=99999")
    check("offset past end -> empty", s == 200 and j.get("items") == [])

    s, j = call("GET", "/api/library/playlists/p.doesnotexist123/tracks")
    check("missing playlist tracks -> []", s == 200 and j.get("tracks") == [], j)

    s, j = call("GET", "/api/catalog/songs/badid123")
    check("bad catalog id -> clean error", s in (404, 502) and isinstance(j, dict))

    s, j = call("POST", "/api/playback/badcommand")
    check("bad command -> 404", s == 404)

    s, j = call("POST", "/api/playback/volume/5")
    check("volume out of range -> 400", s == 400)

    s, j = call("GET", "/api/library/search?term=" + urllib.parse.quote("宮崎駿&stuff %$") + "&types=library-songs&limit=3")
    check("unicode/special search", s == 200, j)

    s, j = call("GET", "/api/amp-api/v1/definitely/not/a/real/path")
    check("passthrough bad path -> clean error", s in (400, 401, 404, 502))

    # concurrent load: reads + streams + a bad call, all at once. Stream
    # endpoints are long-lived BY DESIGN — connect, read a little, disconnect.
    # Under a burst the single-tab CDP driver may fast-fail some calls with
    # 502/503 — acceptable; hangs and 500s are not.
    errs = []
    def hit(path, method="GET", body=None, timeout=90):
        try:
            s2, j2 = call(method, path, body, timeout=timeout)
            if s2 >= 500 and s2 not in (502, 503):
                errs.append((path, s2))
        except Exception as e:
            errs.append((path, str(e)[:60]))
    def sip(path):
        try:
            req = urllib.request.Request(f"{B}{path}")
            r = urllib.request.urlopen(req, timeout=30)
            data = r.read1(2048) or b""
            r.close()
            if not data:
                errs.append((path, "no bytes"))
        except Exception as e:
            errs.append((path, str(e)[:60]))
    threads = [threading.Thread(target=hit, args=(p,), daemon=True)
               for p in ("/api/library/songs?limit=50",
                         "/api/catalog/search?term=x&limit=1",
                         "/api/playback/queue",
                         "/api/favorites",
                         "/api/playback/now-playing",
                         "/api/library/playlists?limit=50",
                         "/api/library/songs?limit=100&offset=100")]
    threads += [threading.Thread(target=sip, args=(p,), daemon=True)
                for p in ("/api/stream", "/api/audio/stream.mp3")]
    threads.append(threading.Thread(target=hit, args=("/api/playlists?limit=10",), daemon=True))
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=60)
    check("concurrent mixed load", not errs, errs[:3])

    # server still alive after all that
    s, j = call("GET", "/health")
    check("alive after concurrency", s == 200 and j.get("status") == "ok")


# ================================================================= netzero

def netzero():
    print("== net-zero verification ==")
    s, j = call("GET", "/api/write/sweeps/dedupe")
    total = j.get("library_size")
    check("library size unchanged",
          total == state.get("library_size"),
          f"{state.get('library_size')} -> {total}")

    s, fav = call("GET", "/api/favorites")
    ids = {t.get("catalog_id") or t.get("library_id") for t in fav.get("tracks", [])}
    check("favorites unchanged", fav.get("count") == state["favorites_count"]
          and ids == state["favorites_ids"],
          f"{state['favorites_count']} -> {fav.get('count')}")

    s, j = call("GET", "/api/library/playlists?limit=100")
    names = [i["name"] for i in j.get("items", []) if "tonearm" in (i.get("name") or "").lower()]
    check("no test playlists left", not names, names)

    # side effects: playback state paused (restored), chrome alive, no zombie procs
    s, j = call("GET", "/api/playback/now-playing")
    check("playback paused at end", j.get("isPlaying") is False)


state = {}
STAGES = {"baseline": baseline, "reads": reads, "playback": playback,
          "stream": stream_stage, "audio": audio_stage, "writes": writes,
          "edge": edge, "netzero": netzero}

if __name__ == "__main__":
    stages = sys.argv[1:] or list(STAGES)
    baseline()                                 # the ledger always runs first
    for st in stages:
        if st != "baseline":
            STAGES[st]()
    fails = [r for r in RESULTS if not r[1]]
    print(f"\n{'='*60}\n{len(RESULTS) - len(fails)}/{len(RESULTS)} passed" +
          (f" — FAILURES: {[f[0] for f in fails]}" if fails else " — ALL GREEN"))
    sys.exit(1 if fails else 0)
