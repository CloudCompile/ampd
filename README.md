# ampd 🎧

**A personal, self-hosted Apple Music API.** ampd drives your own logged-in
Apple Music web player session through Chrome DevTools and exposes it as a
clean local REST API — including corners of Apple's API that aren't officially
documented.

> ⚠️ **Unofficial.** Not affiliated with Apple. ampd automates *your own*
> account, for *your own* use — it holds your session the same way your
> browser does. That's a gray zone in Apple's ToS; use your judgment and keep
> it private/local.

## How it works

```
your code ──HTTP──▶ ampd (FastAPI, localhost) ──CDP──▶ Chrome (your session)
                                                          │
                                                          ▼
                                                amp-api.music.apple.com
                                          (MusicKit, your auth tokens)
```

The web player ships a full MusicKit client with your auth. ampd attaches to
that page over CDP and evaluates calls in it — so there are **no tokens to
manage**: your session lives in a Chrome profile, exactly like a normal login.
Sign in once, and everything the web player can do becomes an API.

## Setup

```bash
pip install -r requirements.txt

# 1. one-time: sign in (opens a visible Chrome window)
python -m ampd.login

# 2. serve (headless by default)
python -m ampd
# → API docs at http://127.0.0.1:8188/docs
```

## Endpoints

### Library (read) — `/api/library/…`

| Endpoint | Description |
|---|---|
| `GET /library/{resource}?limit&offset&term&extend` | list any resource: `songs`, `albums`, `artists`, `playlists`, `music-videos`, `stations` — fully paginated by the caller |
| `GET /library/{resource}/{id}` | one item, **including its relationships** (e.g. an album's tracks) |
| `GET /library/{resource}/{id}/{relationship}?limit&offset` | a relationship collection, e.g. `artists/{id}/albums` |
| `GET /library/search?term=` | search *your* library (songs/albums/artists/playlists) |
| `GET /library/recently-added?limit` | most recent additions |
| `GET /library/playlists/{id}/tracks` | every track of a playlist (auto-paginated to the end) |

Every item is normalized (`id`, `catalog_id`, `library_id`, `name`, `artist`,
`album`, `artwork` at 600×600, …) **and** carries Apple's full raw
`attributes` blob, so nothing the API exposes is hidden.

### Catalog (read) — `/api/catalog/…`

| Endpoint | Description |
|---|---|
| `GET /catalog/search?term=&types=&limit` | multi-type catalog search (`songs,albums,artists,playlists,stations,curators,music-videos`) |
| `GET /catalog/charts?types=&limit&genre` | top charts |
| `GET /catalog/{resource}?ids=` | fetch items by id |
| `GET /catalog/{resource}/{id}?extend=` | one item (`extend=tracks` inlines its content) |
| `GET /catalog/{resource}/{id}/{relationship}` | e.g. `artists/{id}/albums` |

### Personal — `/api/personal/…`

| Endpoint | Description |
|---|---|
| `GET /personal/recommendations` | For You / Listen Now groups |
| `GET /personal/heavy-rotation` | what you've had on repeat |
| `GET /personal/recently-played` | recently played |
| `GET /personal/made-for-you` | Apple's auto-generated mixes |

### Favorites

| Endpoint | Description |
|---|---|
| `GET /api/favorites` | every song in your auto-generated *Favorite Songs* playlist |

### Playback — `/api/playback/…`

| Endpoint | Description |
|---|---|
| `GET /now-playing` | what's playing (transport state; metadata is best-effort) |
| `POST /play\|pause\|toggle\|next\|previous` | transport controls |
| `POST /play-song/{catalog_id}` | play a catalog song |
| `POST /play-collection?kind=album\|playlist\|station&id=` | queue and play a whole collection |
| `GET /queue` | current queue |
| `GET /settings` · `GET /volume` | shuffle / repeat / volume / state |
| `POST /volume/{0..1}` · `POST /shuffle/{on,off}` · `POST /repeat/{0,1,2}` | set them |

### Sweeps — `/api/write/sweeps/…` (batch ops, dry-run by default)

| Endpoint | What it does |
|---|---|
| `GET /sweeps/dedupe` | plan: duplicate library rows (same catalog id or same name+artist+duration) |
| `POST /sweeps/dedupe?execute=1` | remove all-but-first row of each dup group |
| `GET /sweeps/rate?artist=&album=&limit=` | plan: which songs a batch-heart would touch |
| `POST /sweeps/rate?artist=creo&execute=1` | heart them (skips already-hearted; never clears) |
| `GET /sweeps/never-played` | read-only report (Apple's API doesn't expose play counts — flagged when so) |

Every sweep returns a PLAN unless `execute=1`. A full library walk is
~100 s for a 9k-song library; sweep calls are slow by design.

### Streaming — `/api/stream` (SSE) + `/demo`

```
GET /api/stream        # text/event-stream
  event: snapshot      # full player state on connect
  event: update        # every change: play/pause, track, ~1/s progress,
                       # queue changes, shuffle/repeat, volume
```

One `EventSource` drives a whole custom UI — no polling loops. Every event
carries a complete mini-snapshot (title, artist, album, art, playhead,
volume, shuffle/repeat), so clients are dumb renderers.

**A working demo ships at `/demo`** — a single-file remote control
(now-playing card, transport, volume, queue) built on nothing but the
public API. ~100 lines of HTML/JS: use it, or steal it as a starting point
for your own UI. It stays readable when `AMPD_API_KEY` is set via
`/demo?api_key=…` and `/api/stream?api_key=…`.

### Audio — `/api/audio/stream.mp3` (the actual sound)

Metadata streaming is great for a remote control on the same machine — but
if the server runs on a VPS and your UI at home wants to **hear** it, set
`AMPD_AUDIO=1`. ampd then:

1. runs Chrome on a virtual display (`AMPD_AUDIO_DISPLAY=:2`) instead of
   headless — headless Chrome has no audio output,
2. routes its audio into a **private** PulseAudio null sink
   (`AMPD_AUDIO_SINK=ampd_audio`) — your desktop's audio never mixes in,
3. captures the sink and re-serves it as a live mp3
   (`AMPD_AUDIO_BITRATE=160k`):

```html
<audio src="http://vps:8188/api/audio/stream.mp3">
```

That's the whole client. ~1–2 s behind the reported playhead (encoder
buffer); the demo's 🔇/🔊 button is the example. Needs `pulseaudio`,
`pulseaudio-utils`, `ffmpeg` and `Xvfb` on the box (the Docker image has
them). `/api/audio/status` reports pipeline state and listener count.

### The escape hatch

```
ANY /api/amp-api/{any apple music api path}?{query}
```

Forwards your request to `amp-api.music.apple.com` with your tokens injected.
Any method, any path — if the web player can do it, this can too:

```bash
curl 'http://127.0.0.1:8188/api/amp-api/v1/me/library/songs?limit=5'
```

### Writes — `/api/write/…` (ALL disabled by default → `501`)

`POST/DELETE /write/favorites/{id}?library_key=` · `GET/PUT /write/ratings/songs/{id}?rating=like|none` ·
`POST /write/library/add` (body: bare JSON array of catalog ids) ·
`DELETE /write/library/{library_song_id}` ·
`POST /write/playlists?name=&description=` ·
`POST /write/playlists/{id}/tracks` (body: catalog id array — auto-adds songs to your library) ·
`PUT /write/playlists/{id}/tracks` (body: bare JSON array of **library** ids, full ordered
list — this is both reorder and removal) ·
`PATCH /write/playlists/{id}?name=&description=` · `DELETE /write/playlists/{id}`

Every mutation returns `501` until you set `AMPD_ENABLE_WRITES=1`. All shapes
above were validated live against a real account.

## Configuration (env vars)

| Variable | Default | Meaning |
|---|---|---|
| `AMPD_PROFILE` | `~/.config/ampd/chrome-profile` | Chrome profile used for your session |
| `AMPD_CDP_URL` | `http://127.0.0.1:9222` | Chrome debug endpoint (attach or launch) |
| `AMPD_AUTO_CHROME` | `1` | launch Chrome automatically if not reachable |
| `AMPD_HEADLESS` | `1` | headless chrome (set `0` for audible playback) |
| `AMPD_HOST` / `AMPD_PORT` | `127.0.0.1` / `8188` | bind address |
| `AMPD_API_KEY` | *(unset)* | require `Authorization: Bearer <key>` on all routes |
| `AMPD_ENABLE_WRITES` | `0` | unlocks favorite/playlist mutations |
| `AMPD_FAV_PLAYLIST` | `Favorite Songs` | name of the favorites auto-playlist |
| `AMPD_AUDIO` | `0` | stream the actual audio at `/api/audio/stream.mp3` |
| `AMPD_AUDIO_DISPLAY` | `:2` | virtual display for audible chrome |
| `AMPD_AUDIO_SINK` | `ampd_audio` | private pulse sink to capture |
| `AMPD_AUDIO_BITRATE` | `160k` | mp3 bitrate of the audio stream |

## Field notes (the parts the docs won't tell you)

Things learned by driving a real account — encoded in the code so you don't
have to rediscover them:

* **Top-level JS declarations leak.** Chrome keeps `const`/`let` from previous
  `Runtime.evaluate` calls; a redeclaration throws and kills your loop. Always
  IIFE-wrap evals.
* **The favorites endpoint is key-sensitive.** Catalog songs unfavorite via
  `ids[songs]=<catalogId>`, but some library tracks are keyed by their
  *library* id: `ids[library-songs]=i.XXX`. A wrong-key `DELETE` still returns
  `204` — silently doing nothing. Always verify with a fresh read.
* **Library playlists paginate via `next` links**; the web UI's DOM, by
  contrast, is virtualized and will lie to any scraper that trusts what's
  rendered.
* **Playlist track removal and reorder are one call.** `DELETE …/tracks`
  always 400s ("No mode supplied" — nobody knows what mode is). Instead,
  `PUT` the *entire* ordered library-id list: omitted tracks are removed,
  a different order is a reorder. Catalog ids don't work here — only
  `library-songs` ids.
* **Adding a catalog song to a library playlist silently adds it to your
  library.** Deleting the playlist does not undo that.
* **Library adds are 202-async** — the song appears (and can create a
  library-album row for its single) a few seconds later. Verify with a
  retried read, not the response code.
* **Ratings: like or nothing.** `PUT /v1/me/ratings/songs/{id}` with
  `{"value": 1}` = like; `DELETE` clears. A dislike value is *accepted*
  but silently stores as 1 — so ampd doesn't expose it.
* **A heart IS a rating.** Favoriting a song is just `value: 1` on the
  ratings endpoint — so `DELETE` on a rating *removes a heart the user
  set*. Never clear a rating "to verify"; read the prior value first.
  (This bit us once: a test cleared a pre-existing favorite.)
* **No favorites sync needed.** Apple auto-collects hearts into a
  "Favorite Songs" library playlist within seconds of hearting, and
  un-hearts leave just as fast. ampd only reads it.
* **MusicKit memoizes `api.music` GETs** — a read right after a mutation
  returns the stale cached response, and cache-busting with `_=` gets
  rejected ("Parameter '_' is not allowed"). ampd reads via raw
  token-injected fetches instead.
* **Apple's `next` links drop the `limit` param.** Follow them as-is and
  every page after the first silently shrinks to 25 rows — and a naive
  page cap makes you believe the library ends long before it does
  (ampd's author thought 1,325 songs; the truth was 9,045). ampd
  re-applies the original limit on every page.
* **`match=` is a MusicKit-client-only extension** — the raw amp-api
  rejects it (400 "Parameter 'match' is not allowed"). Filter locally.
* **A favorite toggle for songs without a catalog page** (odd uploads /
  region-blocked entries) is only reachable through the library-keyed form.
* **Leaked tabs zombify Chrome.** Dozens of automation tabs → renderers stop
  answering → evals hang for the full socket timeout. ampd reuses a single
  tab and closes sockets with a short timeout on purpose.

## Roadmap

- [x] library/catalog/personal read surface
- [x] write ops: favorites, ratings (like/clear), library add/remove,
      playlist create/add/reorder/remove/rename/delete, queue
      play-next/play-later — all validated live
- [x] now-playing metadata: full title/artist/album/artwork/progress via
      `mk.nowPlayingItem` (the web player's MusicKit exposes it publicly)
- [x] library sweeps: dedupe, batch-rate, never-played report — dry-run by default
- [x] docker packaging + deploy guides (VPS/Railway/fly/Render)
- [x] streaming API (`/api/stream`, SSE) + demo player UI at `/demo` —
      custom front-ends are now a first-class use case

## Deploying

ampd is a long-lived process driving a real, logged-in Chrome — that rules
out serverless (Vercel, Lambda, Cloud Run *jobs*): there is no way to keep a
persistent browser session there. Everything else works:

### VPS (the reference setup)

```bash
docker compose up -d --build
curl localhost:8188/health   # -> {"status":"ok","browser":"authorized"}
```

The Chrome profile lives on the `ampd-data` volume. To sign in, make a
profile on any machine with a screen, then drop it into the volume:

```bash
# on any desktop with a screen, from a source checkout:
AMPD_PROFILE=$HOME/ampd-profile python -m ampd.login   # sign in, press Enter
# then, from the compose project on the server:
tar -C $HOME/ampd-profile -c . | docker compose exec -T ampd tar -x -C /data/.config/ampd/chrome-profile
```

(The profile is just a Chrome user-data-dir — copying it copies the session.
After a re-login once, the headless server reuses it until Apple logs it out,
which is rare.)

### Railway / fly.io

Same image, same volume mount at `/data` (Railway: "Volumes", fly:
`fly volumes create`). Set `AMPD_API_KEY` before exposing publicly.

### Render

Works, but needs a **paid persistent disk** mounted at `/data` — the free
tier's ephemeral filesystem wipes your Apple session on every deploy.

### Tunnels (optional)

A tunnel is just a reverse proxy in front of port 8188 — nothing in ampd
depends on it. If you want one, run cloudflared as a second container with
`--url http://ampd:8188` and set `AMPD_API_KEY` first. ampd itself never
needs to know.

## License

MIT — see [LICENSE](LICENSE).
