"""Discord Rich Presence bridge (v0.5 #96) — opt-in, zero new deps.

AMPD_DISCORD=1 + AMPD_DISCORD_CLIENT_ID=<app id> puts your session's
now-playing into a LOCAL Discord client's presence (this only makes sense
when ampd runs on a desktop that runs Discord — on a headless box the
socket below simply doesn't exist and the bridge logs that and idles).

Design:
* **Opt-in import, opt-in runtime.** Nothing loads unless AMPD_DISCORD=1,
  and the bridge is ~150 lines of raw IPC — no pypresence dependency, the
  base install stays exactly as lean as it was.
* **No eval polling.** Presence is driven by the state the SSE stream
  ALREADY emitted (`routes.stream.last_snapshot`) — the bridge never asks
  Chrome for anything.
* **Paused/stalled → CLEAR, never freeze.** A paused wrong track in your
  profile is worse than no presence: pause or stale state clears the
  activity immediately.
* **Throttled like Discord wants.** Presence updates only on track change
  (the end-timestamp makes Discord tick the progress itself — no per-second
  pushes to hit its rate limit).

Protocol: Discord's local IPC socket — 4-byte LE opcode + 4-byte LE length
+ JSON. Handshake once, then SET_ACTIVITY frames. Every failure mode
(no socket, closed client, rate limit) degrades to "log once, retry in a
minute" — the bridge can never take the server down.
"""
import json
import logging
import os
import socket
import struct
import threading
import time
import uuid

from .config import config

log = logging.getLogger("ampd.discord")

OP_HANDSHAKE = 0
OP_FRAME = 1
OP_CLOSE = 2
OP_PING = 3
OP_PONG = 4

POLL_SECS = 5          # how often to look at the stream's state
RETRY_SECS = 60        # after a failed connect/update — log once, wait


def _ipc_path():
    """Discord's local socket: $XDG_RUNTIME_DIR (or /tmp)/discord-ipc-N.
    Try N = 0..9 — multi-client Discord installs number them."""
    base = os.environ.get("XDG_RUNTIME_DIR") or "/tmp"
    for n in range(10):
        p = os.path.join(base, f"discord-ipc-{n}")
        if os.path.exists(p):
            return p
    return os.path.join(base, "discord-ipc-0")


def _send(sock, op, payload):
    data = json.dumps(payload).encode()
    sock.sendall(struct.pack("<II", op, len(data)) + data)


def _recv(sock):
    header = b""
    while len(header) < 8:
        chunk = sock.recv(8 - len(header))
        if not chunk:
            return None, None
        header += chunk
    op, length = struct.unpack("<II", header)
    data = b""
    while len(data) < length:
        chunk = sock.recv(length - len(data))
        if not chunk:
            return None, None
        data += chunk
    return op, json.loads(data) if data else {}


def _set_activity(sock, activity):
    _send(sock, OP_FRAME, {
        "cmd": "SET_ACTIVITY",
        "args": {"pid": os.getpid(), "activity": activity},
        "nonce": str(uuid.uuid4()),
    })
    return _recv(sock)


def _activity_from(state):
    """The stream event -> Discord activity. details/state are Discord's
    two lines (details = bold top line); end-timestamp lets the CLIENT tick
    the progress between pushes."""
    if not state.get("isPlaying") or not state.get("title"):
        return None
    act = {"details": state["title"],
           "state": state.get("artist") or "Apple Music"}
    if state.get("durationMs") and state.get("elapsedMs") is not None:
        end = time.time() + max(0, (state["durationMs"] -
                                    state["elapsedMs"]) / 1000)
        act["timestamps"] = {"end": int(end)}
    assets = {}
    if state.get("album"):
        assets["large_text"] = state["album"]
    if assets:
        act["assets"] = assets
    return act


def _bridge_loop(client_id):
    sock = None
    last_sig = object()          # something no event can equal
    while True:
        try:
            from .routes.stream import last_snapshot
            snap = last_snapshot()
            act = _activity_from(snap)
            sig = (snap.get("title"), snap.get("artist"),
                   snap.get("isPlaying"))
            if sig != last_sig or act is not None:
                if sock is None:
                    sock = socket.socket(socket.AF_UNIX,
                                         socket.SOCK_STREAM)
                    sock.settimeout(10)
                    sock.connect(_ipc_path())
                    _send(sock, OP_HANDSHAKE,
                          {"v": 1, "client_id": client_id})
                    _recv(sock)
                    log.info("discord: connected, presence live "
                             "(client %s)", client_id)
                _set_activity(sock, act)            # None clears presence
                last_sig = sig
                if act is None:
                    time.sleep(POLL_SECS)
                continue
        except Exception as e:
            # no Discord client, socket vanished, rate limit — all the
            # same: log once per failure streak, drop the socket, wait
            if sock is not None:
                log.warning("discord: presence dropped (%s) — retrying in "
                            "%ds", str(e)[:120], RETRY_SECS)
            try:
                if sock:
                    sock.close()
            except Exception:
                pass
            sock = None
            last_sig = object()      # force a re-push after reconnect
            time.sleep(RETRY_SECS)
            continue
        time.sleep(POLL_SECS)


def start():
    """Spawn the bridge thread. Opt-in import by design: AMPD_DISCORD=1
    only. Never raises — a Discord hiccup must not take the server down."""
    if not config.discord_enabled:
        return
    if config.mock_enabled:
        log.info("discord: skipped in mock mode (synthetic playback would "
                 "be a lie in your profile)")
        return
    client_id = config.discord_client_id
    if not client_id:
        log.warning("discord: AMPD_DISCORD=1 but no AMPD_DISCORD_CLIENT_ID "
                    "— bridge disabled")
        return
    threading.Thread(target=_bridge_loop, args=(client_id,),
                     name="ampd-discord", daemon=True).start()
    log.info("discord: bridge started (client %s)", client_id)
