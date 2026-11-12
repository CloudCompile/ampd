"""Refresh docs/pwa.png — a real screenshot of the PWA shell.

Drives a THROWAWAY headless Chrome (separate port, temp profile — never
tonearm's own renderer) over raw CDP:
  1. load the tonearm origin
  2. inject the API key into localStorage (the PWA's auth dialect)
  3. reload, wait for the SSE snapshot + library to render
  4. capture the viewport

Usage: python3 web/screenshot.py [base_url] [api_key] [out_path]
  base_url defaults to http://127.0.0.1:8200 (localhost only — the
  screenshot never needs the tunnel), key defaults to TONEARM_API_KEY.
"""
import base64
import json
import os
import sys
import tempfile
import time
import urllib.request

import websocket

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8200"
KEY = sys.argv[2] if len(sys.argv) > 2 else os.environ.get("TONEARM_API_KEY", "")
OUT = sys.argv[3] if len(sys.argv) > 3 else os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "docs", "pwa.png")
PORT = 9333


def cdp_http(path, method="GET"):
    req = urllib.request.Request(f"http://127.0.0.1:{PORT}{path}",
                                 method=method)
    return json.loads(urllib.request.urlopen(req, timeout=10).read())


def wait_server(proc, timeout=30):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if proc.poll() is not None:
            raise SystemExit("screenshot chrome died on startup")
        try:
            cdp_http("/json/version")
            return
        except Exception:
            time.sleep(0.4)
    raise SystemExit("screenshot chrome never opened the debug port")


def main():
    import subprocess
    profile = tempfile.mkdtemp(prefix="tonearm-shot-")
    proc = subprocess.Popen([
        "google-chrome", f"--user-data-dir={profile}",
        f"--remote-debugging-port={PORT}", "--no-sandbox", "--disable-gpu",
        "--headless=new", f"--window-size=1600,1000", "--hide-scrollbars",
        "about:blank"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    wait_server(proc)
    try:
        tabs = cdp_http("/json/list")
        ws_url = next(t["webSocketDebuggerUrl"] for t in tabs
                      if t.get("type") == "page")
        ws = websocket.create_connection(ws_url, timeout=30,
                                         max_size=100 * 1024 * 1024)
        n = [0]

        def call(method, deadline_s=30, **params):
            n[0] += 1
            deadline = time.time() + deadline_s
            ws.send(json.dumps({"id": n[0], "method": method,
                                "params": params}))
            while time.time() < deadline:
                try:
                    msg = json.loads(ws.recv())
                except websocket.WebSocketTimeoutException:
                    continue        # recv slice expired — check the deadline
                if msg.get("id") == n[0]:
                    if "error" in msg:
                        raise RuntimeError(f"{method}: {msg['error']}")
                    return msg.get("result", {})
            raise RuntimeError(f"{method} timed out")

        call("Page.enable")
        call("Page.navigate", url=BASE + "/")
        time.sleep(4)                       # shell + first fetches
        if KEY:
            call("Runtime.evaluate", returnByValue=True,
                 expression=f"localStorage.setItem('tonearm_key', {json.dumps(KEY)})")
            call("Page.navigate", url=BASE + "/")   # reload with the key
        time.sleep(10)                      # SSE snapshot + library render
        shot = call("Page.captureScreenshot", format="png")["data"]
        with open(OUT, "wb") as f:
            f.write(base64.b64decode(shot))
        print(f"screenshot -> {OUT} ({len(shot)} b64 chars)")
        ws.close()
    finally:
        proc.terminate()
        proc.wait(timeout=10)


if __name__ == "__main__":
    main()
