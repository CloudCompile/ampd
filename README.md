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

`POST/DELETE /write/favorites/{id}` · `POST /write/library/add` ·
`POST /write/playlists` · `POST/DELETE /write/playlists/{id}/tracks` ·
`PATCH /write/playlists/{id}` · `DELETE /write/playlists/{id}` ·
`PUT /write/ratings/songs/{id}`

Every mutation returns `501` until you set `AMPD_ENABLE_WRITES=1`. The stubs
are shaped after the calls we've validated by hand against a real account.

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
* **A favorite toggle for songs without a catalog page** (odd uploads /
  region-blocked entries) is only reachable through the library-keyed form.
* **Leaked tabs zombify Chrome.** Dozens of automation tabs → renderers stop
  answering → evals hang for the full socket timeout. ampd reuses a single
  tab and closes sockets with a short timeout on purpose.

## Roadmap

- [x] library/catalog/personal read surface
- [ ] enable write ops: favorites, playlist add/remove, ratings
- [ ] library sweeps (batch re-rating, dedupe) — overnight jobs, behind the writes flag
- [ ] now-playing metadata (transport state works; the web player's custom
      MusicKit build keeps the queue internals private — needs a hook into its
      playback-state events)
- [ ] docker packaging

## License

MIT — see [LICENSE](LICENSE).
