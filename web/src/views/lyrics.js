// Synced lyrics view (#89) — implements the contract documented in
// docs/lyrics-contract.md verbatim: active_line = last line with
// timeMs <= interpolatedElapsed + offsetMs. Fetch per id change, cache,
// 404 = a quiet "instrumental" state (never an error).
import { get } from "../api.js";
import { esc } from "../util.js";

const panel = document.getElementById("lyr");
const linesEl = document.getElementById("lyr-lines");
let lines = [];
let lyricsId = null;
let rendered = -2;
const cache = new Map();       // id -> lines | null (null = honest 404)
let offsetMs = 0;

document.getElementById("lyrClose").onclick = () => { panel.hidden = true; };
document.getElementById("offMinus").onclick = () =>
  setOffset(Math.max(offsetMs - 100, -5000));
document.getElementById("offPlus").onclick = () =>
  setOffset(Math.min(offsetMs + 100, 5000));
function setOffset(v) { offsetMs = v; document.getElementById("off").textContent = v; }
setOffset(-1500);              // audio listeners start ~1.5s behind the playhead

export function toggle() { panel.hidden = !panel.hidden; }
export function visible() { return !panel.hidden; }

export async function onState(s) {
  if (!s) return;
  if ((s.id || null) !== lyricsId) {
    lyricsId = s.id || null;
    lines = [];
    rendered = -2;
    if (!lyricsId) { linesEl.textContent = "nothing playing"; return; }
    if (cache.has(lyricsId)) {
      lines = cache.get(lyricsId) || [];
      paint();
    } else {
      linesEl.textContent = "…";
      try {
        const j = await get(`/api/catalog/songs/${encodeURIComponent(lyricsId)}/lyrics`);
        lines = (j.lines || []).filter((l) => l.timeMs != null);
        cache.set(lyricsId, lines);
      } catch {
        cache.set(lyricsId, null);
        lines = [];
      }
      if (!lines.length) linesEl.textContent = "instrumental / no lyrics available";
      else paint();
    }
  }
}

function paint() {
  linesEl.innerHTML = lines.map((l) =>
    `<div>${(l.text || "♪").replace(/[&<>]/g,
      (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]))}</div>`).join("");
}

// the contract, verbatim from the doc
function activeLineIndex(ls, elapsed, off) {
  let active = -1;
  for (let i = 0; i < ls.length; i++)
    if (ls[i].timeMs <= elapsed + off) active = i;
    else break;
  return active;
}

function interpolatedElapsed(st) {
  if (!st || st.elapsedMs == null) return 0;
  const drift = st.isPlaying ? Math.max(0, Date.now() - (st.ts || Date.now())) : 0;
  return Math.min(st.elapsedMs + drift, st.durationMs ?? Infinity);
}

// render loop: recompute at animation pace, touch the DOM on line change only
function tick() {
  if (!panel.hidden && lines.length) {
    const i = activeLineIndex(lines, interpolatedElapsed(stateRef()), offsetMs);
    if (i !== rendered) {
      rendered = i;
      for (let k = 0; k < linesEl.children.length; k++)
        linesEl.children[k].className = k === i ? "active" : "";
      if (i >= 0 && linesEl.children[i])
        linesEl.children[i].scrollIntoView({ block: "center", behavior: "smooth" });
    }
  }
  requestAnimationFrame(tick);
}
let _state = null;
export function noteState(s) { _state = s; }
function stateRef() { return _state; }
requestAnimationFrame(tick);
