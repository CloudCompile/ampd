# tonearm needs a real Chrome next to the API — the whole point is driving YOUR
# logged-in web player session. One container, one process tree.
#
#   docker build -t tonearm .
#   docker run -d -p 8188:8188 -v tonearm-data:/data tonearm
#
# First-time sign-in: profiles are plain Chrome user-data-dirs, so sign in
# once on any desktop (see README "Deploying") and drop the profile into the
# /data volume — or run with --headless=0 on a machine with a display.

# ---- stage 1: build the PWA (#84) — node exists ONLY here -----------------
FROM node:22-slim AS webbuild
WORKDIR /src
COPY web/package.json web/package-lock.json* ./
RUN npm ci --no-audit --no-fund 2>/dev/null || npm install --no-audit --no-fund
COPY web/ web/
RUN node web/build.mjs            # -> /src/tonearm/web-dist

# ---- stage 2: the runtime — Chrome + pulse + ffmpeg, NO node --------------
FROM python:3.12-slim

# chromium (Debian) + fonts so Apple's UI renders and any screenshot isn't tofu
# pulseaudio + xvfb + ffmpeg: audio streaming (TONEARM_AUDIO=1) — chrome runs on
# a virtual display, its output is captured from a private null sink and
# re-served as mp3 at /api/audio/stream.mp3
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      chromium fonts-liberation fonts-noto-color-emoji ca-certificates \
      pulseaudio xvfb ffmpeg \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY tonearm/ tonearm/
# the built PWA from stage 1 — AFTER `COPY tonearm/` so it is not clobbered
COPY --from=webbuild /src/tonearm/web-dist tonearm/web-dist

# HOME points at the volume so the default chrome profile
# (~/.config/tonearm/chrome-profile) persists across container upgrades.
ENV HOME=/data \
    TONEARM_CHROME_BIN=/usr/bin/chromium \
    TONEARM_HOST=0.0.0.0 \
    TONEARM_PORT=8188 \
    XDG_RUNTIME_DIR=/tmp/pulse-run
RUN mkdir -p /tmp/pulse-run && chmod 777 /tmp/pulse-run
VOLUME /data
EXPOSE 8188

# non-root; /data volume must be writable by uid 1000
RUN useradd -u 1000 -m -d /data tonearm && chown -R tonearm /data /app
USER tonearm

# Docker treats a failed healthcheck by marking the container unhealthy — it
# does NOT restart it on its own. Pair with `restart: unless-stopped` (compose)
# or an autoheal sidecar (plain `docker run`) — see README "Deploying".
# /health is exempt from TONEARM_API_KEY auth, so this works with a key set.
# start-period is generous because first boot launches Chrome.
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:%s/health' % os.environ.get('TONEARM_PORT','8188'), timeout=4)"

CMD ["python", "-m", "tonearm"]
