"""One-time sign-in helper: opens a HEADED chrome on the tonearm profile so you
can sign in to your Apple account. After this, the headless server reuses it."""
import subprocess
import sys
import time

from .config import config


def main():
    print("Opening a visible Chrome window on the tonearm profile…")
    print("Sign in to https://music.apple.com, then come back here.")
    proc = subprocess.Popen([
        config.chrome_bin,
        f"--user-data-dir={config.profile_dir}",
        "--remote-debugging-port=" + config.cdp_url.rsplit(":", 1)[-1],
        "--no-first-run", "--no-default-browser-check",
        "https://music.apple.com",
    ])
    try:
        input("\nPress Enter here AFTER you've signed in and can see your library… ")
    finally:
        print("Leaving that window open — tonearm can attach to it, or close it and run headless.")
        print("(If you close it, just start the server: it relaunches headless with your session.)")


if __name__ == "__main__":
    main()
