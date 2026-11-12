"""ampd configuration — everything overridable via environment variables."""
import os
from pathlib import Path

class Config:
    # --- browser / CDP ---
    # Path to a Chrome profile used ONLY for ampd (sign in once via `python -m ampd login`)
    profile_dir: str = os.environ.get("AMPD_PROFILE",
                                      str(Path.home() / ".config" / "ampd" / "chrome-profile"))
    # Attach to an already-running Chrome with a debug port, or auto-launch one
    cdp_url: str = os.environ.get("AMPD_CDP_URL", "http://127.0.0.1:9222")
    auto_chrome: bool = os.environ.get("AMPD_AUTO_CHROME", "1") == "1"
    chrome_bin: str = os.environ.get("AMPD_CHROME_BIN", "google-chrome")
    headless: bool = os.environ.get("AMPD_HEADLESS", "1") == "1"

    # --- local API ---
    host: str = os.environ.get("AMPD_HOST", "127.0.0.1")
    port: int = int(os.environ.get("AMPD_PORT", "8188"))
    # Optional shared secret; if set, all /api routes require "Authorization: Bearer <key>"
    api_key: str = os.environ.get("AMPD_API_KEY", "")
    # Make the unauthenticated non-localhost bind FATAL instead of a loud
    # warning. Default warn-only because inside a container binding 0.0.0.0
    # is normal and correct (the port mapping is the boundary).
    strict_bind: bool = os.environ.get("AMPD_STRICT_BIND", "0") == "1"

    # --- behavior ---
    # WRITE OPS ARE OFF BY DEFAULT. Favorites/playlists mutations return 501 until
    # you explicitly set AMPD_ENABLE_WRITES=1.
    enable_writes: bool = os.environ.get("AMPD_ENABLE_WRITES", "0") == "1"
    # Name of the auto-playlist Apple generates for favorited songs
    favorites_playlist_name: str = os.environ.get("AMPD_FAV_PLAYLIST", "Favorite Songs")

    # --- renderer watchdog ---
    # Background pinger for the music tab. A stalled renderer usually recovers
    # on its own within ~60s — so a tab is only "dead" after watchdog_tries
    # CONSECUTIVE failed pings; then it's recycled and hot-recovered instead
    # of waiting for the next request to fail.
    watchdog: bool = os.environ.get("AMPD_WATCHDOG", "1") == "1"
    watchdog_interval: int = int(os.environ.get("AMPD_WATCHDOG_INTERVAL", "20"))
    watchdog_tries: int = int(os.environ.get("AMPD_WATCHDOG_TRIES", "3"))

    # --- audio streaming (so a UI on YOUR computer can HEAR what the server plays)
    # AMPD_AUDIO=1 makes ampd run chrome on a virtual display, route its audio
    # into a private PulseAudio null sink, capture that, and re-serve it as a
    # live mp3 stream at /api/audio/stream.mp3. Requires pulse, ffmpeg, Xvfb.
    audio_enabled: bool = os.environ.get("AMPD_AUDIO", "0") == "1"
    audio_display: str = os.environ.get("AMPD_AUDIO_DISPLAY", ":2")
    audio_sink: str = os.environ.get("AMPD_AUDIO_SINK", "ampd_audio")
    audio_bitrate: str = os.environ.get("AMPD_AUDIO_BITRATE", "160k")

config = Config()
