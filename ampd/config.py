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

    # --- behavior ---
    # WRITE OPS ARE OFF BY DEFAULT. Favorites/playlists mutations return 501 until
    # you explicitly set AMPD_ENABLE_WRITES=1.
    enable_writes: bool = os.environ.get("AMPD_ENABLE_WRITES", "0") == "1"
    # Name of the auto-playlist Apple generates for favorited songs
    favorites_playlist_name: str = os.environ.get("AMPD_FAV_PLAYLIST", "Favorite Songs")

config = Config()
