# Roadmap

How this list thinks:

* tonearm rides **undocumented surfaces**. Apple can change any of them without
  notice — items touching them carry a *verify live* gate before build.
* **Effort**: S (< day) · M (days) · L (a week+). **Priority**: P0 (next
  phase) · P1 (soon) · P2 (when it's fun).
* Nothing here circumvents DRM or exceeds the logged-in session's
  entitlements — see [Non-goals](#non-goals).

Shipped in v0.1: full read surface (library/catalog/personal/favorites,
lyrics, hints, export), playback with queue + settings round-trips, SSE
state streaming, live audio streaming, write ops (favorites, ratings,
library, playlist lifecycle), net-zero-tested sweeps, Docker + deploy
guides, live test suite, CI.

---

## v0.2 — Bulletproof

*Reliability and operations. The server must survive Apple's flakiness and
its own renderer.*

- [x] **Renderer watchdog** — proactively ping the tab; on stall, recycle it
      and hot-recover instead of waiting for the next call to fail `M P0`
- [x] **Read cache + request coalescing** — TTL cache for library/catalog
      GETs, identical in-flight reads collapse into one CDP eval, mutations
      bust by key `M P0`
- [x] **Docker HEALTHCHECK** wired to `/health` + restart-policy guidance in
      the deploy guides `S P0`
- [x] **Non-localhost warning** — refuse (or warn loudly) when binding
      0.0.0.0 without `TONEARM_API_KEY` `S P0`
- [x] **Prometheus `/metrics`** — eval latency histogram, renderer-stall
      counter, Apple 4xx/5xx rates, stream listeners, queue depth `S P1`
- [x] **ARM64 images** — buildx multi-arch for RPi / Apple Silicon `S P1`
- [x] **`/api/debug` surface** — last-N CDP calls with durations, current
      tab URL, renderer health snapshot `S P1`
- [x] **Apple 429/backoff handling** in the in-page fetch layer `M P1`

## v0.3 — Memory

*Persistence. Apple's API forgets; tonearm shouldn't.*

- [x] **Backup/restore** — recreate playlists from `/api/library/export`
      (the missing half; export is already a complete restore reference) `M P0`
- [x] **Local SQLite store (opt-in)** — durable play history (poll
      now-playing), library snapshot, sync state `L P0`
- [x] **Incremental library sync + `GET /api/library/diff?since=`** —
      return only rows changed since a timestamp `M P1`
- [x] **Recently-played archive** — Apple only ever returns ~20 items;
      keep everything from here on `S P1`
- [x] **Scheduled exports** — cron inside the container, retention policy `S P1`
- [x] **Listening stats** — top artists/tracks/plays per day/week/all-time
      from the local store `M P2`

## v0.4 — Typed API & clients

*The OpenAPI page currently lies by omission (untyped dicts). Make it truth.*

- [x] **Pydantic response models for every route** — real schema, real
      validation `L P0`
- [x] **Generated clients** — TypeScript + Python, published from CI `M P1`
- [x] **Standard error envelope** — `{error: {code, hint}}` everywhere, with
      a table in the README `S P1`
- [x] **Mock server mode** — seeded synthetic fixtures so UI devs never need
      an Apple account `M P1`

## v0.5 — Listening experience

*For the UI at home.* **Shipped in v0.5.0.**

- [x] **Proper web UI (PWA)** — library browse, search, queue drag, synced
      lyrics; the demo was a proof, this is a product `L P0`
- [x] **Synced-lyrics contract** — pair `/catalog/songs/{id}/lyrics` lines
      with the SSE playhead; publish the client recipe `S P0`
- [x] **Audio options** — opus/ogg in addition to mp3, bitrate profiles,
      loudness normalization `M P1`
- [x] **OBS overlay endpoint** — now-playing as JSON/text for streamers `S P2`
- [x] **Per-listener join offset** — audio clients start at the current
      playhead instead of wherever the encoder ring is `M P2`
- [x] **Discord Rich Presence bridge** — now-playing as activity status `M P2`
- [x] **Last.fm scrobble bridge** — opt-in, from the local history store `M P2`

## v0.6 — Automation

*Apple has no webhooks. tonearm can be the webhook.* **Shipped in v0.6.0.**

- [x] **Outbound webhooks** — POST events (track change, heart, playlist
      mutation, stall-recovered) to user-configured URLs, with retries `M P0`
      `tonearm/webhooks.py` · `/api/webhooks` · `TONEARM_WEBHOOKS=1`.
      At-least-once delivery, backoff 2s/10s/30s/120s/600s, non-retryable 4xx
      dead-letter, optional HMAC-SHA256 signing (`X-Tonearm-Signature`).
      Producers ride existing state only: the stream-hook buffer, write
      routes, the watchdog, the snapshot walk — zero new eval kinds.
- [x] **Scheduled sweep digests** — dry-run dedupe/never-played reports to a
      webhook on a schedule `S P1` — `tonearm/digest.py` ·
      `TONEARM_DIGEST_INTERVAL` (needs webhooks); on-demand twin at
      `GET /api/write/sweeps/digest`. One walk feeds both reports.
- [ ] **New-release watcher** — poll followed artists' catalog pages, notify
      + optionally auto-add to a playlist `M P1`
      *Blocked on a verify-live gate:* library artists are keyed by library
      ids (`r.xxx`) and the mapping to catalog artist ids is not documented —
      the lookup strategy (attributes vs search) must be validated against a
      real account before anything ships.
- [ ] **Smart-playlist engine** — rule sets ("added after X, artist in Y")
      materialized as live playlists `L P2`
- [ ] **Home Assistant recipes** — media_player-style integration examples
      `S P2` (the webhook events above are already the payload half)

## v0.7 — Multi-user

*Carefully. One Apple session is one stream — by design, not by accident.*

- [ ] **Multi-key auth with scopes** — `read` keys for friends' UIs, `write`
      keys for yours; per-key rate ceilings `M P0`
- [ ] **Per-key audit log** — who did what, exportable `S P1`
- [ ] **Multi-account support** — a second Apple profile behind a selector
      header `L P2`
- [ ] **Party mode** — shared queue with voting (research how far one
      session can be pushed) `L P2`

## v1.0 — Polish

1.0 means: surface stable, documented, backed up, observable.

- [ ] **Docs site** — mkdocs on GitHub Pages, endpoint reference generated
      from the typed schemas `M P1`
- [ ] **Install script + systemd generator** — bare-metal setup in one
      command `S P1`
- [ ] **Recorded-fixture offline harness in CI** — the live suite stays
      manual; CI gains fixture-driven regression coverage `M P1`
- [ ] **API freeze** — deprecation policy for route/shape changes `S P0`

## Moonshots

* Not obviously useful yet, obviously fun eventually:
  GraphQL-style batch endpoint · multi-storefront (region as a param) ·
  "tonearm bridge" for Jellyfin/Plex metadata · a tiny ESP32 now-playing
  display recipe · voice-control skill.

## Non-goals

* **DRM circumvention or downloading.** The audio stream is a live pipe of
  the user's own entitled session — not a downloader, and never will be.
* **Multi-stream sharing.** One Apple session = one audible stream. That's a
  ToS-respecting property, not a limitation.
* **Scraping beyond the session's entitlements** or impersonating official
  Apple clients.
* **Being a product.** tonearm is a personal tool that happens to be public.
