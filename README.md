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

### Library (read)

| Endpoint | Description |
|---|---|
| `GET /api/library/playlists` | all playlists in your library |
| `GET /api/library/playlists/{id}/tracks` | every track of a playlist (auto-paginated) |
| `GET /api/library/songs?limit&offset` | library songs, one page |
| `GET /api/library/recently-added` | recent library additions |
| `GET /api/library/search-catalog?term=` | search the Apple Music catalog |

### Favorites

| Endpoint | Description |
|---|---|
| `GET /api/favorites` | every song in your auto-generated *Favorite Songs* playlist |

Write operations (`POST/DELETE /api/favorites/{id}`) are **stubbed out by
default** — they return `501` until you set `AMPD_ENABLE_WRITES=1`.

### Playback

| Endpoint | Description |
|---|---|
| `GET /api/playback/now-playing` | what's playing |
| `POST /api/playback/play\|pause\|toggle\|next\|previous` | transport controls |
| `POST /api/playback/play-song/{catalog_id}` | play a catalog song |
| `GET /api/playback/queue` | current queue |

Playback works wherever Chrome has an audio device — run with `AMPD_HEADLESS=0`
if you want to see (and hear) the player.

### The escape hatch

```
ANY /api/amp-api/{any apple music api path}?{query}
```

Forwards your request to `amp-api.music.apple.com` with your tokens injected.
Any method, any path — if the web player can do it, this can too:

```bash
curl 'http://127.0.0.1:8188/api/amp-api/v1/me/library/songs?limit=5'
```

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

- [ ] enable write ops: favorites, playlist add/remove
- [ ] library sweeps (batch re-rating, dedupe) — overnight jobs, behind the writes flag
- [ ] now-playing metadata (transport state works; the web player's custom
      MusicKit build keeps the queue internals private — needs a hook into its
      playback-state events)
- [ ] docker packaging

## License

MIT — see [LICENSE](LICENSE).
