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

    # --- mock mode (v0.4) ---
    # AMPD_MOCK=1 serves the full API from seeded synthetic fixtures — no
    # Apple account, no Chrome, no network. For UI devs, contributors and
    # CI integration tests (plain urllib, no TestClient needed).
    mock_enabled: bool = os.environ.get("AMPD_MOCK", "0") == "1"

    # --- local store (v0.3 "Memory") ---
    # OFF by default: every store-backed surface answers 501 honestly until
    # you opt in. The db holds listening history + library snapshots on YOUR
    # volume; nothing leaves the machine.
    store_enabled: bool = os.environ.get("AMPD_STORE", "0") == "1"
    # How often (seconds) the background library snapshot walk runs. The walk
    # is ~1 eval/page of ~100 songs — slow cadence by design, skipped while
    # the watchdog reports a renderer stall.
    store_sync_interval: int = int(os.environ.get("AMPD_STORE_SYNC_INTERVAL",
                                                  "21600"))
    # Keep this many play-history rows at most (0 = unbounded); the archive
    # is the point of the store, so the default is generous.
    store_history_max: int = int(os.environ.get("AMPD_STORE_HISTORY_MAX",
                                                "200000"))

    # --- scheduled exports (v0.3 #28) ---
    # 0 = OFF (default — a full export walk is heavy). When on: one full
    # /api/library/export every N seconds, keep-N files in the export dir.
    export_interval: int = int(os.environ.get("AMPD_EXPORT_INTERVAL", "0"))
    export_keep: int = int(os.environ.get("AMPD_EXPORT_KEEP", "7"))

    @classmethod
    def store_db_path(cls):
        """Where the sqlite file lives. Explicit env wins; else the /data
        volume (docker convention, HOME=/data there anyway); else under the
        user's local state dir."""
        env = os.environ.get("AMPD_STORE_PATH", "")
        if env:
            return env
        if os.path.isdir("/data"):
            return "/data/ampd.db"
        return str(Path.home() / ".local" / "share" / "ampd" / "store.db")

config = Config()
