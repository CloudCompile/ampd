# Changelog

All notable changes to tonearm are documented here. Format:
[keep-a-changelog](https://keepachangelog.com/en/1.1.0/); versions follow
[SemVer](https://semver.org/) until 1.0 (then the [freeze
policy](docs/deprecation.md) governs breaking changes).

Release notes for each version are drafted by `scripts/release_notes.py`
(merged PRs since the previous tag) and edited by hand before publishing.

## [Unreleased]

### Added
- **The freeze** (#50, #126–128): documented deprecation policy
  ([docs/deprecation.md](docs/deprecation.md)), `Deprecation:`/`Sunset:`
  headers middleware, the pinnable surface marker (`/health` `surface`
  field + `X-Tonearm-Surface` header), and the OpenAPI contract gate —
  CI diffs every PR's schema against `api/openapi.json` and fails
  breaking changes that didn't ride the policy.
- **This docs site** (#129–131): mkdocs-material on GitHub Pages,
  deployed on release tags; the API reference is generated from the
  OpenAPI snapshot with a route-coverage check; the env table and field
  notes are generated from the README (which stays the source of truth).
- CHANGELOG + release-notes automation (#138).

### Fixed
- Audio pipeline teardown: a duplicate `Pipeline.stop()` (smuggled in by
  the #162 rename) defeated the #177 process-group kill — parecord/ffmpeg
  lingered forever after the last stream listener left (#200).
- CDP deadlock: the renderer watchdog armed only on a READY MusicKit
  tab, so a renderer that died before first-ready wedged the whole API
  layer forever. The watchdog now arms when the websocket connects.
  CDP recv slices tightened to 5s so deadlines are honored (~10s fail,
  was ~60s) (#201).
- `TONEARM_CHROME_EXTRA`: pass extra chrome args for constrained hosts.

## [0.7.0] — 2026-11-13 — Multi-user

### Added
- **Multi-key auth** (#192): scoped keys (`read`/`write`) in a 0600
  hash-only registry, per-key 60s rate ceilings (429 + `Retry-After`),
  per-key SSE connection caps, per-key request metrics, and a
  `python3 -m tonearm keys` CLI. The master key keeps full access.
- **Audit trail** (#193): every authenticated mutation is recorded
  (store table + 1000-ring fallback), `GET /api/audit` master-only,
  bodies never logged.
- **Session truth in `/health`** (#194): `session: ok|expired|unknown` —
  a dead session reads 502 `session_expired` with a "run login" hint
  instead of lying healthy.
- Docker images on ghcr for 0.7.0, generated clients refreshed.

## [0.6.2] — 2026-11-13 — Live-session hardening

### Fixed
- CDP busy-storm: busy-waiters no longer close the shared websocket
  (they retry without touching the socket) (#174).
- Apple 429s map to `rate_limited` with `Retry-After` (#175).
- The release watcher skips stale boots and runs on a 180s time budget
  (#176); pipeline subprocesses die with the server (#177).
- Progress-proof plays: the history writer only records plays that
  actually progressed (#178).

## [0.6.1] / [0.6.0] — 2026-11-12 — Automation

### Added
- Webhooks + scheduled digest emails (#164)
- Multi-key groundwork and generated clients (#165, #166, #168)
- The release watcher, smart playlists, and Home Assistant recipes (#167)

## [0.5.x] — 2026-11-12 — Listening experience

### Added
- Queue management (`PUT /api/playback/queue`), opus/ogg formats,
  loudnorm, playhead-aligned joins (#152)

### Fixed
- The queue-reorder MusicKit dance, live-tested (#159)

## [0.4.0] — 2026-11-12 — Typed API & clients

### Added
- Pydantic response models on every JSON route (CI-enforced), the
  standard error envelope, generated TypeScript/Python clients (#195
  continues this), tarball releases.

## [0.3.0] — 2026-11-12 — Memory (the local store)

### Added
- Local SQLite store: library, plays (history writer), snapshots;
  `TONEARM_STORE=1`.

## [0.2.x] — 2026-11-12 — Bulletproof

### Added
- Read cache with single-flight coalescing, 429 backoff, watchdog,
  SSE live events.

## [0.1.0] — 2026-11-11 — First public release (as ampd)

### Added
- Playback control, library/catalog search, favorites, the demo page,
  audio streaming at `/api/audio/stream.mp3`.

[Unreleased]: https://github.com/CloudCompile/tonearm/compare/v0.7.0...HEAD
[0.7.0]: https://github.com/CloudCompile/tonearm/compare/v0.6.2...v0.7.0
[0.6.2]: https://github.com/CloudCompile/tonearm/compare/v0.6.1...v0.6.2
[0.6.1]: https://github.com/CloudCompile/tonearm/compare/v0.6.0...v0.6.1
[0.6.0]: https://github.com/CloudCompile/tonearm/compare/v0.5.1...v0.6.0
[0.5.x]: https://github.com/CloudCompile/tonearm/compare/v0.4.0...v0.5.1
[0.4.0]: https://github.com/CloudCompile/tonearm/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/CloudCompile/tonearm/compare/v0.2.1...v0.3.0
[0.2.x]: https://github.com/CloudCompile/tonearm/compare/v0.1.0...v0.2.1
[0.1.0]: https://github.com/CloudCompile/tonearm/releases/tag/v0.1.0
