# Security Policy

## Reporting a vulnerability

Please use GitHub's **private vulnerability reporting** (Security tab →
Report a vulnerability) rather than a public issue.

## Scope and threat model, honestly stated

tonearm drives Apple Music through a real logged-in browser session. That
means:

* **Whoever can reach the API can control your Apple Music account** —
  playback, library mutations, playlists. Bind it to localhost, put it
  behind a VPN/tunnel with auth, or set `TONEARM_API_KEY`.
* **Binding beyond loopback without a key is guarded.** tonearm refuses to
  start (exit 2) if `TONEARM_STRICT_BIND=1` and it would bind a non-localhost
  address with no `TONEARM_API_KEY`; by default it prints an unmistakable
  warning instead (warn-only because inside a container, `0.0.0.0` is the
  normal, correct bind — the port mapping is the boundary).
* **`TONEARM_ENABLE_WRITES=1` unlocks mutations.** It ships off for a reason.
* tonearm is unofficial and unaffiliated with Apple; the surface it automates
  can change without notice.
* Don't run it on a shared box — the Chrome profile it drives holds your
  Apple session cookies.
