# Synced-lyrics contract

Pairing lyric lines with the SSE playhead — the exact recipe, so every
client (demo page, PWA, your thing) highlights the same line at the same
moment. Pure client-side: no evals, no extra server round-trips beyond the
two documented GETs.

## Inputs

**1. The playhead — SSE, never polling.**

```
const es = new EventSource('/api/stream');     // ?api_key=… when keyed
es.addEventListener('snapshot', e => setState(JSON.parse(e.data)));
es.addEventListener('update',   e => setState(JSON.parse(e.data)));
```

Each event carries:

| field        | meaning                                              |
|--------------|------------------------------------------------------|
| `id`         | now-playing item id (what you resolve lyrics FOR)    |
| `elapsedMs`  | playhead position at capture time                    |
| `durationMs` | track length                                         |
| `ts`         | wall-clock ms (client-comparable) at capture         |
| `isPlaying`  | play/pause — interpolation only advances while true  |

`elapsedMs` updates ~1/s while playing. **Don't render at 1 Hz** — the line
highlights would visibly lag. Interpolate (step 3).

**2. The lines — one fetch per track.**

```
GET /api/catalog/songs/{id}/lyrics
-> { "song_id": "1440…", "lines": [
      { "text": "we tune the instruments of the night",
        "timeMs": 12340, "endTimeMs": 15540 }, … ] }
```

`timeMs` is the sync point. Lines are sorted ascending. **404 = no lyrics**
— library-only tracks and instrumentals hit this constantly; render a quiet
"instrumental / no lyrics available" state and move on. Cache per `id` in
memory for the session; lyrics never change mid-session.

## The math

```js
// 1. interpolate the playhead between SSE events (render loop, ~60 fps)
function nowElapsed(ev, isPlaying) {
  if (!ev || ev.elapsedMs == null) return 0;
  const drift = isPlaying ? (Date.now() - ev.ts) : 0;
  return Math.min(ev.elapsedMs + drift, ev.durationMs ?? Infinity);
}

// 2. the contract:
//    active_line = the LAST line with timeMs <= elapsed + offsetMs
function activeLineIndex(lines, elapsedMs, offsetMs) {
  let active = -1;
  for (let i = 0; i < lines.length; i++)
    if (lines[i].timeMs <= elapsedMs + offsetMs) active = i;
    else break;
  return active;                       // -1 = before the first line
}

// 3. render loop — recompute ~4x/s is plenty; CSS transitions smooth it
function tick() {
  const elapsed = nowElapsed(state, state.isPlaying);
  const i = activeLineIndex(lines, elapsed, OFFSET_MS);
  if (i !== lastRendered) highlight(i);   // scroll into view, transition
  lastRendered = i;
}
```

## The offset (`offsetMs`)

```
offsetMs = userNudgeMs - sinkLagMs
```

- **sinkLagMs** — how far BEHIND the playhead your output is. The audio
  stream `/api/audio/stream.mp3` is ~1–2 s behind the reported playhead
  (capture + encode + browser buffer), so audio listeners start around
  `-1500`. Pure remote control (no sound) uses `0`.
- **userNudgeMs** — a small ± slider (±2000, step 100). Apple's TTML timing
  and your ears disagree sometimes; the contract doesn't pretend otherwise.

`active_line` is a pure function of `(lines, elapsed, offsetMs)` — no
hysteresis, no timers of its own. Same inputs, same line, everywhere.

## Anti-patterns (all seen in the wild)

- **Polling `now-playing` for lyrics** — 1 Hz jumpy highlights and extra
  Chrome evals per poll; the SSE stream already pushes everything.
- **`setInterval(track-duration/lines.length)`** — assuming even spacing;
  real TTML timing is not linear.
- **Re-fetching lyrics on every SSE event** — fetch per `id` change, cache.
- **Blocking the render on the fetch** — keep the playhead moving; fill the
  lines in when they arrive.
- **Treating 404 as an error** — it is the normal answer for instrumentals.

## Reference implementation

`/demo` ships a working implementation (toggle `lyrics` in the demo card):
fetch-on-id-change, rAF interpolation, offset slider, graceful 404. Steal
it — that page is ~200 lines and is the intended starting point for
custom UIs.
