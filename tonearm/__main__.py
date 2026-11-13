"""`python -m tonearm` → start the API server."""
import logging
import os
import sys

import uvicorn

from .config import config

log = logging.getLogger("tonearm")

_LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1", ""}


def bind_guard():
    """Warn loudly (or refuse, with TONEARM_STRICT_BIND=1) when binding beyond
    loopback without an API key.

    Why not always refuse: inside a container, binding 0.0.0.0 is NORMAL and
    correct — the port mapping is the security boundary, and refusing would
    break the documented Docker quickstart. So the default posture is an
    unmistakable warning; TONEARM_STRICT_BIND=1 makes it fatal (pick that on a
    multi-tenant host where another tenant could reach the port)."""
    if config.host in _LOCAL_HOSTS or config.api_key:
        return
    detail = (
        f"TONEARM IS EXPOSED WITHOUT AUTH — host={config.host!r} binds beyond "
        f"loopback and TONEARM_API_KEY is unset. Anyone who can reach this port "
        f"can read your library, listening history and lyrics, and play "
        f"audio through your account.\n"
        f"  fix: set TONEARM_API_KEY=<secret> (requests then need "
        f"'Authorization: Bearer <secret>'), or bind to loopback "
        f"(TONEARM_HOST=127.0.0.1).\n"
        f"  inside a container this bind is expected — the port mapping is "
        f"the boundary; set TONEARM_STRICT_BIND=1 to make this condition fatal.")
    if config.strict_bind:
        log.error("refusing to start: %s", detail)
        raise SystemExit(2)
    if os.path.exists("/.dockerenv"):
        log.warning("bind guard: %s", detail)
    else:
        # bare-metal exposure is the dangerous case — escalate visually
        print("=" * 72, file=sys.stderr)
        print(detail, file=sys.stderr)
        print("=" * 72, file=sys.stderr)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(name)s %(levelname)s %(message)s")
    # subcommands: `login` (one-time sign-in) and `keys` (the multi-key
    # CLI). Everything else boots the server. (#170: the README documented
    # subcommands the dispatch ignored — the server just started, which is
    # a confusing way to learn the port is taken.)
    if len(sys.argv) > 1 and sys.argv[1] in ("login", "keys"):
        if sys.argv[1] == "login":
            from .login import main as sub_main
        else:
            # keys.main() parses sys.argv[1:] itself — drop the "keys" word
            sys.argv = [sys.argv[0]] + sys.argv[2:]
            from .keys import main as sub_main
        sub_main()
        raise SystemExit(0)
    bind_guard()
    uvicorn.run("tonearm.main:app", host=config.host, port=config.port,
                log_level="info")