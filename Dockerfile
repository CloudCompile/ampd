# ampd needs a real Chrome next to the API — the whole point is driving YOUR
# logged-in web player session. One container, one process tree.
#
#   docker build -t ampd .
#   docker run -d -p 8188:8188 -v ampd-data:/data ampd
#
# First-time sign-in: profiles are plain Chrome user-data-dirs, so sign in
# once on any desktop (see README "Deploying") and drop the profile into the
# /data volume — or run with --headless=0 on a machine with a display.
FROM python:3.12-slim

# chromium (Debian) + fonts so Apple's UI renders and any screenshot isn't tofu
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      chromium fonts-liberation fonts-noto-color-emoji ca-certificates \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ampd/ ampd/

# HOME points at the volume so the default chrome profile
# (~/.config/ampd/chrome-profile) persists across container upgrades.
ENV HOME=/data \
    AMPD_CHROME_BIN=/usr/bin/chromium \
    AMPD_HOST=0.0.0.0 \
    AMPD_PORT=8188
VOLUME /data
EXPOSE 8188

# non-root; /data volume must be writable by uid 1000
RUN useradd -u 1000 -m -d /data ampd && chown -R ampd /data /app
USER ampd

CMD ["python", "-m", "ampd"]
