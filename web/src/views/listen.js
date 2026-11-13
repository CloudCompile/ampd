// Remote listening: the SERVER plays (its headless chrome drives Apple);
// this wires an <audio> element to the live mp3 stream so the human on the
// other side of the wire hears it. Only surfaces when TONEARM_AUDIO=1 —
// the probe answers honestly and the button stays hidden otherwise.
import { get } from "../api.js";

export function initListen() {
  const btn = document.getElementById("listen");
  if (!btn) return;
  get("/api/audio/status").then((s) => {
    if (s && (s.enabled || s.running || s.sink)) btn.hidden = false;
  }).catch(() => { /* audio off — stays hidden */ });

  btn.addEventListener("click", () => {
    let a = document.getElementById("remote-audio");
    if (!a) {
      const key = localStorage.getItem("tonearm_key") || "";
      a = document.createElement("audio");
      a.id = "remote-audio";
      // EventSource dialect: the audio element cannot send headers either
      a.src = `/api/audio/stream.mp3${
        key ? `?api_key=${encodeURIComponent(key)}` : ""}`;
      a.autoplay = true;
      document.body.appendChild(a);
    }
    if (a.paused) {
      a.play().catch(() => {
        btn.textContent = "🔇 stream down";
      });
      btn.textContent = "🔊 listening";
      btn.classList.add("on");
    } else {
      a.pause();
      btn.textContent = "🔊 listen";
      btn.classList.remove("on");
    }
  });
}
