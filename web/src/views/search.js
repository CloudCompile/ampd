// Search (#86): one box, two scopes — your library, then the catalog.
// Debounced 250ms; keyboard-first (arrow keys move, Enter plays, Esc closes).
import { get, post } from "../api.js";
import { esc } from "../util.js";

const box = document.getElementById("q");
const out = document.getElementById("searchout");
const scopeEl = document.getElementById("search-scope");
const listEl = document.getElementById("search-list");
let hits = [];
let sel = -1;
let t = null;

function close() {
  out.hidden = true;
  box.value = "";
  hits = [];
}

function render() {
  scopeEl.textContent = hits.length
    ? `${hits.length} result${hits.length === 1 ? "" : "s"} — library first, then catalog`
    : "no results";
  listEl.innerHTML = hits.map((h, i) => `
    <div class="row${i === sel ? " now" : ""}" data-i="${i}" style="position:relative">
      <div class="t"><b>${esc(h.name)}</b><span>${esc(h.artist || "")}</span></div>
      <span class="badge">${esc(h.source)}</span>
    </div>`).join("");
}

function pick(i) {
  const h = hits[i];
  if (!h) return;
  if (h.source.startsWith("library"))
    post("/api/playback/play-collection",
         { kind: h.kind.replace(/^library-/, "").replace(/s$/, ""),
           resource_id: h.id });
  else if (h.catalog_id || h.id)
    post(`/api/playback/play-song/${h.catalog_id || h.id}`);
}

box.addEventListener("input", () => {
  clearTimeout(t);
  t = setTimeout(run, 250);                     // debounced (#86)
});

box.addEventListener("keydown", (e) => {
  if (e.key === "Escape") return close();
  if (!hits.length) return;
  if (e.key === "ArrowDown") { sel = Math.min(sel + 1, hits.length - 1); render(); }
  if (e.key === "ArrowUp") { sel = Math.max(sel - 1, 0); render(); }
  if (e.key === "Enter") pick(sel);
});

listEl.addEventListener("click", (e) => {
  const row = e.target.closest(".row");
  if (row) pick(+row.dataset.i);
});

async function run() {
  const term = box.value.trim();
  if (!term) return close();
  out.hidden = false;
  scopeEl.textContent = "searching…";
  hits = [];
  sel = -1;
  try {
    // library first (what you can play RIGHT NOW)
    const lib = await get("/api/library/search", { term, limit: 15 });
    for (const [kind, rows] of Object.entries(lib))
      for (const r of rows)
        hits.push({ ...r, kind, source: `library · ${kind.replace("library-", "")}` });
    // then the catalog (what you can ADD)
    const cat = await get("/api/catalog/search", { term, types: "songs", limit: 10 });
    for (const r of (cat.songs || []))
      hits.push({ ...r, kind: "songs", source: "catalog" });
  } catch { /* keyed down mid-keystroke — next input re-runs */ }
  render();
}
