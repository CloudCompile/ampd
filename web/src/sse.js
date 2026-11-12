// One EventSource for the whole app (#88) — steal the demo's wiring:
// snapshot on connect, updates after, reconnect on error. The api_key
// dialect rides the query string (EventSource cannot send headers).

let es = null;
const listeners = new Set();

export function onState(fn) { listeners.add(fn); }

let state = null;
export function currentState() { return state; }

function connect() {
  // the key dialect (#90): EventSource cannot send headers, so the key
  // rides the query string — the server accepts either dialect
  const key = localStorage.getItem("tonearm_key") || "";
  es = new EventSource("/api/stream" + (key ? `?api_key=${encodeURIComponent(key)}` : ""));
  es.addEventListener("snapshot", (e) => {
    state = JSON.parse(e.data);
    listeners.forEach((fn) => fn(state));
  });
  es.addEventListener("update", (e) => {
    state = JSON.parse(e.data);
    listeners.forEach((fn) => fn(state));
  });
  es.onerror = () => {
    document.getElementById("conn").classList.add("off");
    es.close();
    setTimeout(connect, 2000);
  };
  es.onopen = () =>
    document.getElementById("conn").classList.remove("off");
}
connect();
