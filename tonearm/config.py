"""tonearm configuration — everything overridable via environment variables."""
import os
from pathlib import Path

class Config:
    # --- browser / CDP ---
    # Path to a Chrome profile used ONLY for tonearm (sign in once via `python -m tonearm login`)
    profile_dir: str = os.environ.get("TONEARM_PROFILE",
                                      str(Path.home() / ".config" / "tonearm" / "chrome-profile"))
    # Attach to an already-running Chrome with a debug port, or auto-launch one
    cdp_url: str = os.environ.get("TONEARM_CDP_URL", "http://127.0.0.1:9222")
    auto_chrome: bool = os.environ.get("TONEARM_AUTO_CHROME", "1") == "1"
    chrome_bin: str = os.environ.get("TONEARM_CHROME_BIN", "google-chrome")
    headless: bool = os.environ.get("TONEARM_HEADLESS", "1") == "1"

    # --- local API ---
    host: str = os.environ.get("TONEARM_HOST", "127.0.0.1")
    port: int = int(os.environ.get("TONEARM_PORT", "8188"))
    # Optional shared secret; if set, all /api routes require "Authorization: Bearer <key>"
    api_key: str = os.environ.get("TONEARM_API_KEY", "")
    # Make the unauthenticated non-localhost bind FATAL instead of a loud
    # warning. Default warn-only because inside a container binding 0.0.0.0
    # is normal and correct (the port mapping is the boundary).
    strict_bind: bool = os.environ.get("TONEARM_STRICT_BIND", "0") == "1"

    # --- behavior ---
    # WRITE OPS ARE OFF BY DEFAULT. Favorites/playlists mutations return 501 until
    # you explicitly set TONEARM_ENABLE_WRITES=1.
    enable_writes: bool = os.environ.get("TONEARM_ENABLE_WRITES", "0") == "1"
    # Name of the auto-playlist Apple generates for favorited songs
    favorites_playlist_name: str = os.environ.get("TONEARM_FAV_PLAYLIST", "Favorite Songs")

    # --- renderer watchdog ---
    # Background pinger for the music tab. A stalled renderer usually recovers
    # on its own within ~60s — so a tab is only "dead" after watchdog_tries
    # CONSECUTIVE failed pings; then it's recycled and hot-recovered instead
    # of waiting for the next request to fail.
    watchdog: bool = os.environ.get("TONEARM_WATCHDOG", "1") == "1"
    watchdog_interval: int = int(os.environ.get("TONEARM_WATCHDOG_INTERVAL", "20"))
    watchdog_tries: int = int(os.environ.get("TONEARM_WATCHDOG_TRIES", "3"))

    # --- audio streaming (so a UI on YOUR computer can HEAR what the server plays)
    # TONEARM_AUDIO=1 makes tonearm run chrome on a virtual display, route its audio
    # into a private PulseAudio null sink, capture that, and re-serve it as a
    # live mp3 stream at /api/audio/stream.mp3. Requires pulse, ffmpeg, Xvfb.
    audio_enabled: bool = os.environ.get("TONEARM_AUDIO", "0") == "1"
    audio_display: str = os.environ.get("TONEARM_AUDIO_DISPLAY", ":2")
    audio_sink: str = os.environ.get("TONEARM_AUDIO_SINK", "tonearm_audio")
    audio_bitrate: str = os.environ.get("TONEARM_AUDIO_BITRATE", "160k")
    # loudness normalization (#93): ffmpeg loudnorm in the encoder process —
    # one filter per pipeline, fanned out post-encode, no extra subprocesses
    audio_loudnorm: bool = os.environ.get("TONEARM_AUDIO_LOUDNORM", "0") == "1"
    # join alignment (#95): pad a new listener's feed with pre-encoded
    # silence so clients get a deterministic alignment point. 0 disables.
    audio_join_pad: bool = os.environ.get("TONEARM_AUDIO_JOIN_PAD", "1") == "1"

    # --- Discord Rich Presence (v0.5, opt-in) ---
    # TONEARM_DISCORD=1 + TONEARM_DISCORD_CLIENT_ID put the session's now-playing
    # into a LOCAL Discord client's presence. Zero new deps (raw IPC);
    # paused/stalled clears presence instead of freezing a wrong track.
    discord_enabled: bool = os.environ.get("TONEARM_DISCORD", "0") == "1"
    discord_client_id: str = os.environ.get("TONEARM_DISCORD_CLIENT_ID", "")

    # --- Last.fm scrobbler (v0.5, opt-in) ---
    # TONEARM_LASTFM=1 scrobbles from the store's play history (50%/4-min rule,
    # dedupe persisted on (id, started_at)). One-time auth: python -m
    # tonearm.lastfm — creds land in a 0600 file.
    lastfm_enabled: bool = os.environ.get("TONEARM_LASTFM", "0") == "1"
    lastfm_api_key: str = os.environ.get("TONEARM_LASTFM_API_KEY", "")
    lastfm_secret: str = os.environ.get("TONEARM_LASTFM_SECRET", "")

    def lastfm_creds_path(self):
        return (os.environ.get("TONEARM_LASTFM_CREDS")
                or os.path.join(os.path.dirname(self.store_db_path()),
                                "lastfm.json"))

    # --- outbound webhooks (v0.6 Automation, opt-in) ---
    # Apple has no webhooks. tonearm can be the webhook: track changes,
    # write mutations, renderer recoveries and library diffs are POSTed to
    # user-configured URLs, with retries. The hook list is managed through
    # /api/webhooks and persisted to a 0600 JSON file on the volume.
    webhooks_enabled: bool = os.environ.get("TONEARM_WEBHOOKS", "0") == "1"
    webhook_attempts: int = int(os.environ.get("TONEARM_WEBHOOK_ATTEMPTS", "5"))
    webhook_timeout: float = float(os.environ.get("TONEARM_WEBHOOK_TIMEOUT",
                                                 "10"))
    # park a URL after this many consecutive dead letters (#100): it stops
    # receiving events for a cooldown instead of retrying forever. A real
    # success resets the streak and unparks immediately.
    webhook_park_after: int = int(os.environ.get("TONEARM_WEBHOOK_PARK_AFTER",
                                                "3"))
    webhook_park_s: float = float(os.environ.get("TONEARM_WEBHOOK_PARK_S",
                                                 "900"))

    def webhooks_config_path(self):
        return (os.environ.get("TONEARM_WEBHOOKS_FILE")
                or os.path.join(os.path.dirname(self.store_db_path()),
                                "webhooks.json"))

    # --- scheduled sweep digests (v0.6, opt-in) ---
    # 0 = OFF. When on (and TONEARM_WEBHOOKS=1), one dry-run dedupe/never-
    # played digest is POSTed as a `sweep.digest` event every N seconds.
    digest_interval: int = int(os.environ.get("TONEARM_DIGEST_INTERVAL", "0"))

    # --- mock mode (v0.4) ---
    # TONEARM_MOCK=1 serves the full API from seeded synthetic fixtures — no
    # Apple account, no Chrome, no network. For UI devs, contributors and
    # CI integration tests (plain urllib, no TestClient needed).
    mock_enabled: bool = os.environ.get("TONEARM_MOCK", "0") == "1"

    # --- local store (v0.3 "Memory") ---
    # OFF by default: every store-backed surface answers 501 honestly until
    # you opt in. The db holds listening history + library snapshots on YOUR
    # volume; nothing leaves the machine.
    store_enabled: bool = os.environ.get("TONEARM_STORE", "0") == "1"
    # How often (seconds) the background library snapshot walk runs. The walk
    # is ~1 eval/page of ~100 songs — slow cadence by design, skipped while
    # the watchdog reports a renderer stall.
    store_sync_interval: int = int(os.environ.get("TONEARM_STORE_SYNC_INTERVAL",
                                                  "21600"))
    # Keep this many play-history rows at most (0 = unbounded); the archive
    # is the point of the store, so the default is generous.
    store_history_max: int = int(os.environ.get("TONEARM_STORE_HISTORY_MAX",
                                                "200000"))

    # --- scheduled exports (v0.3 #28) ---
    # 0 = OFF (default — a full export walk is heavy). When on: one full
    # /api/library/export every N seconds, keep-N files in the export dir.
    export_interval: int = int(os.environ.get("TONEARM_EXPORT_INTERVAL", "0"))
    export_keep: int = int(os.environ.get("TONEARM_EXPORT_KEEP", "7"))

    @classmethod
    def store_db_path(cls):
        """Where the sqlite file lives. Explicit env wins; else the /data
        volume (docker convention, HOME=/data there anyway); else under the
        user's local state dir."""
        env = os.environ.get("TONEARM_STORE_PATH", "")
        if env:
            return env
        if os.path.isdir("/data"):
            return "/data/tonearm.db"
        return str(Path.home() / ".local" / "share" / "tonearm" / "store.db")

config = Config()
