# Contributing

Small personal project, but genuinely open to contributions.

* **Issues first** — describe what you expected vs what happened. If it's a
  bug against a live Apple surface, include the endpoint and the response
  shape (redact ids if you like).
* **Keep the honesty bar** — ampd's README documents what's real vs flaky
  (album adds, empty-playlist 404s, async lag). New features should state
  their caveats the same way.
* **Net-zero testing** — any change to write paths gets exercised against a
  real account with the baseline/undo protocol from `tests/live_test.py`.
  Don't ship a mutation you haven't undone.
* **Style** — plain stdlib where possible, typed where it helps, no new
  heavy dependencies without discussion.

Run locally:

    pip install -r requirements.txt
    AMPD_PORT=8189 python3 -m ampd          # writes and audio are off by default
    AMPD_ENABLE_WRITES=1 python3 -m ampd    # when you mean it
