# tonearm 🎧

Self-hosted Apple Music: your own logged-in web-player session becomes a
personal API — play, search, stream, scrobble, automate — with the real
audio served from your machine.

!!! note "What it is"
    tonearm drives a real Chrome session on music.apple.com (via CDP),
    speaks the same amp-api Apple's web player speaks, and re-serves
    everything as a clean, typed REST surface — plus the actual audio as
    a live mp3/opus stream. It is not affiliated with Apple; it is your
    own session exposed to your own automations.

## Try it in 30 seconds — no Apple account

```bash
git clone https://github.com/CloudCompile/tonearm && cd tonearm
pip install -r requirements.txt
TONEARM_MOCK=1 python3 -m tonearm
# → PWA at http://127.0.0.1:8188 · API docs at /docs
```

## Setup (real account)

```bash
python3 -m tonearm login   # one-time visible Chrome sign-in
python3 -m tonearm         # serve; headless by default
```

## The shape of the thing

- **API-first**: every route is typed, OpenAPI is the contract of
  record (see the [API reference](api-reference.md)), and CI fails on
  breaking changes ([deprecation policy](deprecation.md)).
- **Audio**: `/api/audio/stream.mp3` — what the server plays, your
  machines hear ([env knobs](env.md)).
- **Automation**: webhooks, scheduled digests, a release watcher and
  smart playlists — see the [Home Assistant recipes](ha-recipes.md).
- **Field notes** — the parts Apple's docs won't tell you
  ([read them](field-notes.md)); they're encoded in the code.

## Where to go next

- Install via Docker: `ghcr.io/cloudcompile/tonearm` (tags follow releases)
- Multi-user keys, audit log, per-key limits: see the changelog for 0.7
- The PWA is served by the server itself — dock a phone to it once and
  it installs as an app
