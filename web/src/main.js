// ampd PWA entry — wires the shell: SSE -> now-playing card (#88) + queue
// (#87) + lyrics (#89); tabs -> virtualized library (#85); one search box
// (#86); the key dialect (#90). The demo page was the proof; this is the
// product.
import { get, post } from "./api.js";
import { onState, currentState } from "./sse.js";
import { esc, fmt } from "./util.js";
import * as library from "./views/library.js";
import * as queue from "./views/queue.js";
import * as lyrics from "./views/lyrics.js";

const $ = (id) => document.getElementById(id);

// ---------------- now playing card + transport (#88): SSE-driven ----------
onState((s) => {
  queue.noteSnapshot(s);
  lyrics.noteState(s);
  lyrics.onState(s);
  library.markNow(s.id);
  if (s.title != null) {
    $("np-title").textContent = s.title || "—";
    $("np-artist").textContent = [s.artist, s.album].filter(Boolean).join(" — ");
    $("art").className = "art" + (s.artworkUrl ? "" : " empty");
    $("art").style.backgroundImage =
      s.artworkUrl ? `url(${s.artworkUrl})` : "none";
    $("np-dur").textContent = fmt(s.durationMs);
  }
  $("play").textContent = s.isPlaying ? "⏸" : "▶";
  if (s.elapsedMs != null && s.durationMs)
    $("np-fill").style.width = (100 * s.elapsedMs / s.durationMs) + "%";
  $("np-elapsed").textContent = fmt(s.elapsedMs);
  if (s.volume != null) $("vol").value = s.volume;
  if (s.queue) queue.setQueue(s.queue);
});

async function api(path) {
  await post(path);
}

$("play").onclick = () =>
  api(`/api/playback/${(currentState() || {}).isPlaying ? "pause" : "play"}`);
$("next").onclick = () => api("/api/playback/next");
$("prev").onclick = () => api("/api/playback/previous");
$("vol").onchange = (e) => api(`/api/playback/volume/${e.target.value}`);
$("mute").onclick = () => {
  if ($("vol").value != "0") { $("vol").dataset.last = $("vol").value;
    $("vol").value = 0; $("vol").onchange({ target: $("vol") }); }
  else { $("vol").value = $("vol").dataset.last || .7;
    $("vol").onchange({ target: $("vol") }); }
};
$("art").onclick = () => lyrics.toggle();

// ---------------- tabs (#85 / #87) ----------------
$("tabs").addEventListener("click", (e) => {
  const tab = e.target.closest("button");
  if (!tab) return;
  for (const b of $("tabs").children) b.classList.toggle("on", b === tab);
  $("tabs").dataset.tab = tab.dataset.tab;
  if (tab.dataset.tab === "queue") queue.show();
  else library.show(tab.dataset.tab);
});
library.show("songs");

// ---------------- the key dialect (#90) ----------------
function maybePromptKey(err) {
  if (/401|403/.test(String(err))) $("keyprompt").hidden = false;
}
window.addEventListener("unhandledrejection", (e) => maybePromptKey(e.reason));
$("keysave").onclick = () => {
  localStorage.setItem("ampd_key", $("key").value.trim());
  $("keyprompt").hidden = true;
  location.reload();               // re-fetch everything with the key
};

// the shell loads regardless; a 401 on the first real fetch opens the prompt
(async () => {
  try { await get("/api/playback/now-playing"); }
  catch (e) { maybePromptKey(e); }
})();

// ---------------- service worker (#90: cache the shell, never the API) ----
if ("serviceWorker" in navigator && location.protocol === "https:")
  navigator.serviceWorker.register("/sw.js");
