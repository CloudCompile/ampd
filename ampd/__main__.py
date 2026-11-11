"""`python -m ampd` → start the API server."""
import logging
import os
import sys

import uvicorn

from .config import config

log = logging.getLogger("ampd")

_LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1", ""}


def bind_guard():
    """Warn loudly (or refuse, with AMPD_STRICT_BIND=1) when binding beyond
    loopback without an API key.

    Why not always refuse: inside a container, binding 0.0.0.0 is NORMAL and
    correct — the port mapping is the security boundary, and refusing would
    break the documented Docker quickstart. So the default posture is an
    unmistakable warning; AMPD_STRICT_BIND=1 makes it fatal (pick that on a
    multi-tenant host where another tenant could reach the port)."""
    if config.host in _LOCAL_HOSTS or config.api_key:
        return
    detail = (
        f"AMPD IS EXPOSED WITHOUT AUTH — host={config.host!r} binds beyond "
        f"loopback and AMPD_API_KEY is unset. Anyone who can reach this port "
        f"can read your library, listening history and lyrics, and play "
        f"audio through your account.\n"
        f"  fix: set AMPD_API_KEY=<secret> (requests then need "
        f"'Authorization: Bearer <secret>'), or bind to loopback "
        f"(AMPD_HOST=127.0.0.1).\n"
        f"  inside a container this bind is expected — the port mapping is "
        f"the boundary; set AMPD_STRICT_BIND=1 to make this condition fatal.")
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
    bind_guard()
    uvicorn.run("ampd.main:app", host=config.host, port=config.port,
                log_level="info")