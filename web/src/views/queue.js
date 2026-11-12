// Queue view (#87): rendered FROM the SSE stream state (poll nothing).
// Drag-reorder maps to the full-list PUT contract — send the WHOLE ordered
// id list, never deltas. Last write wins.
import { put } from "../api.js";
import { esc } from "../util.js";

const el = document.getElementById("list");
let queue = [];                       // from the SSE snapshot
let dragI = -1;

function render() {
  el.className = "list";
  el.innerHTML = "<div class='spacer' style='height:" +
    (queue.length * 52) + "px'></div>" + queue.map((t, i) => `
    <div class="row queue-row${t.title === nowTitle() ? " now" : ""}"
         draggable="true" data-i="${i}" style="top:${i * 52}px">
      <span class="handle">≡</span>
      <div class="t"><b>${esc(t.title || t.id)}</b>
        <span>${esc(t.artist || "")}</span></div>
      <span class="badge">#${i + 1}</span>
    </div>`).join("");
}

function nowTitle() {
  const np = document.getElementById("np-title").textContent;
  return np === "—" ? null : np;
}

export async function show() {
  document.getElementById("searchout").hidden = true;
  el.hidden = false;
  render();
}

export function setQueue(items) {
  queue = items || [];
  if (!document.getElementById("searchout").hidden) return;
  if (document.getElementById("tabs").dataset.tab === "queue") render();
}

// --- drag reorder (#87) ---
el.addEventListener("dragstart", (e) => {
  const row = e.target.closest(".queue-row");
  if (!row) return;
  dragI = +row.dataset.i;
  row.classList.add("dragging");
  e.dataTransfer.effectAllowed = "move";
});
el.addEventListener("dragover", (e) => {
  e.preventDefault();
  const row = e.target.closest(".queue-row");
  for (const n of el.querySelectorAll(".queue-row"))
    n.classList.toggle("dropbefore", n === row);
});
el.addEventListener("drop", async (e) => {
  e.preventDefault();
  const row = e.target.closest(".queue-row");
  if (!row || dragI < 0) return;
  const to = +row.dataset.i;
  if (to === dragI) return;
  const ids = queue.map((t) => t.id);
  const [moved] = ids.splice(dragI, 1);
  ids.splice(to, 0, moved);
  // the contract: the WHOLE list, in order (#87)
  await put("/api/playback/queue", { ids });
  queue = ids.map((id) => ({ id, title: titleFor(id) }));
  dragI = -1;
  render();
});
el.addEventListener("dragend", () => {
  dragI = -1;
  for (const n of el.querySelectorAll(".queue-row"))
    n.classList.remove("dragging", "dropbefore");
});

// titles are re-fetched cheaply from the last SSE snapshot
let lastSnapshot = null;
export function noteSnapshot(s) { lastSnapshot = s; }
function titleFor(id) {
  const q = (lastSnapshot && lastSnapshot.queue) || [];
  return (q.find((t) => t.id === id) || {}).title || id;
}
