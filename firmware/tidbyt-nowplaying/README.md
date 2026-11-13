# The dead Tidbyt Gen 2 → tonearm now-playing + speaker + remote

The Tidbyt Gen 2 (the pixel display with the touch pad and speaker)
outlived its company: the hardware is fine, the cloud is gone. The
bootloader is unlocked, so it doesn't have to matter.

This is the build that turns it into:

1. **A now-playing display** — a static CarPlay-style title/album/artist
   stack, a small progress bar and elapsed time, with album art on the
   right and a soft full-panel artwork wash behind it.
2. **A speaker** — the Gen 2's I2S speaker streams tonearm's
   `/api/audio/stream.mp3` live (the same "hear it here" the PWA
   sidebar does).
3. **A gesture remote** — the top pad controls playback:

| Gesture | Action |
|---|---|
| 1 tap | play / pause |
| 2 taps | next track |
| 3 taps | **back** — restart if >10s into the song, else the previous track |
| hold ~1s | play **playlist 1** |
| hold twice | play **playlist 2** |

The display defaults to **auto** mode: when synced lyrics exist, the
right-hand art tile becomes a three-line lyrics tile (previous dim,
current bright, next dim); otherwise it remains album art. The left-side
player never changes. `http://tidbyt.local/` exposes the speaker volume
and display mode controls; the full library remote is served by tonearm
at `/tidbyt`.

The 10s rule lives **server-side** (`POST /api/playback/back`) so the
button stays dumb — Apple's own skipToPreviousItem restarts at ~3s,
which no remote control wants.

## Flash it (once, over USB)

1. Create the device's own scoped key (revocable, rate-capped):

   ```bash
   python3 -m tonearm keys add tidbyt --scopes read,write --rate 120
   ```

2. Fill in the three substitutions at the top of
   [`tidbyt.yaml`](tidbyt.yaml): the funnel URL, the device key, and the
   two playlist ids (`/api/library/playlists`).

3. Flash from Chrome (device plugged in by USB):

   ```bash
   cd firmware/tidbyt-nowplaying
   # version PIN — newer esphome REMOVED the i2s_audio media_player,
   # and the replacement (speaker media player) requires the ESP-IDF
   # framework, which the HUB75 display wrapper doesn't build under.
   # 2025.8.0 is the validated sweet spot: config-validates AND the
   # full firmware compiles (we checked both, in a sandbox).
   pip install "esphome==2025.8.0"
   esphome run tidbyt.yaml
   ```

   (or drag the compiled binary onto https://web.esphome.io)

After that it's WiFi-only: the device talks straight to tonearm's
funnel URL — TLS, rate-capped, scoped. Revoke the key and the remote
goes silent; the display dies with it (give it a read-only key if you
want display-only mode).

## Hardware notes (Gen 2, from the community pin map)

- ESP32-S3 · 64×32 HUB75 matrix (FM6126A driver) · touch pad GPIO33
- Speaker: I2S out — BCLK GPIO12, WS GPIO13, DOUT GPIO14
- Display pins and driver flags: see the yaml (proven by the
  ESPHome-on-Tidbyt-Gen2 thread; we did not have to guess a pin)

## First-boot gotchas

- 2.4 GHz WiFi only.
- The device's http_request can't pin TLS certs under the arduino
  framework (ESP-IDF-only feature) — `verify_ssl: false` is set. The
  scoped key is the auth; the device lives on your LAN. If you want
  cert pinning, that's the IDF migration (and a new display wrapper).
- If the display stays dark: the HUB75 power switch (below) is
  ALWAYS_ON, so it's wiring — reseat the panel ribbon.
- Volume: `POST /api/playback/volume/<0-100>` or any tonearm surface —
  the device's volume is set at boot to 80%.

## Preview files

The repository includes separate full-view previews:

- `docs/tidbyt-preview-auto-lyrics.png`
- `docs/tidbyt-preview-artwork.png`
- `docs/tidbyt-preview-paused.png`
- `docs/tidbyt-preview-idle.png`

## What works vs what's proven

- Config: **validates** on esphome 2025.8.0.
- Full firmware: **compiles** in CI-like sandbox (toolchain + link).
- On-device behavior: needs YOUR hardware — flash and report back.
  The pin map is community-proven (ESPHome-on-Tidbyt-Gen2 thread), so
  the risk is tuning (touch threshold, scroll speed), not wiring.
