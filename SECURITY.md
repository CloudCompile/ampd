# Security Policy

## Reporting a vulnerability

Please use GitHub's **private vulnerability reporting** (Security tab →
Report a vulnerability) rather than a public issue.

## Scope and threat model, honestly stated

ampd drives Apple Music through a real logged-in browser session. That
means:

* **Whoever can reach the API can control your Apple Music account** —
  playback, library mutations, playlists. Bind it to localhost, put it
  behind a VPN/tunnel with auth, or set `AMPD_API_KEY`.
* **`AMPD_ENABLE_WRITES=1` unlocks mutations.** It ships off for a reason.
* ampd is unofficial and unaffiliated with Apple; the surface it automates
  can change without notice.
* Don't run it on a shared box — the Chrome profile it drives holds your
  Apple session cookies.
