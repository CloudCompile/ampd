import { get, post, postJson, putJson, qs, guard, toast, initHeader,
         fmtWhen, esc } from "./common.js";

initHeader("Bench");
const panel = () => document.getElementById("panel");

document.getElementById("tabs").addEventListener("click", e => {
  const b = e.target.closest("button");
  if (!b) return;
  for (const x of document.querySelectorAll("#tabs button"))
    x.classList.toggle("active", x === b);
  ({ playlists: showPlaylists, smartlists: showSmartlists,
     heart: showHeart, restore: showRestore })[b.dataset.t]();
});

// ------------------------------------------------------- playlist editor

async function showPlaylists() {
  panel().innerHTML = `
    <div class="grid2">
      <div><h2 style="margin-top:0">Your playlists</h2><div id="pl-list"><span class="spin"></span></div></div>
      <div><h2 style="margin-top:0">Editor <span class="dim small" id="ed-name"></span></h2><div id="ed">pick a playlist</div></div>
    </div>`;
  try {
    const j = await get("/api/library/playlists?limit=100");
    panel().querySelector("#pl-list").innerHTML = `
      <table>${j.items.map(p =>
        `<tr data-pl="${esc(p.id)}" style="cursor:pointer">
         <td>${esc(p.name)}<div class="dim small">${esc((p.attributes || {}).trackCount ?? "?")} tracks</div></td></tr>`).join("")}</table>`;
    panel().querySelector("#pl-list").addEventListener("click", e => {
      const tr = e.target.closest("[data-pl]");
      if (!tr) return;
      for (const x of panel().querySelectorAll("[data-pl]"))
        x.style.background = "";
      tr.style.background = "var(--panel2)";
      loadEditor(tr.dataset.pl, tr.querySelector("b")?.textContent
        || tr.textContent.trim());
    });
  } catch (e) {
    panel().querySelector("#pl-list").innerHTML = `<div class="dim">${esc(e.message)}</div>`;
  }
}

let editState = null;   // {id, name, tracks:[{id, name, artist}]}

async function loadEditor(id, name) {
  const ed = document.getElementById("ed");
  ed.innerHTML = `<span class="spin"></span>`;
  try {
    const j = await get(`/api/library/playlists/${encodeURIComponent(id)}/tracks`);
    editState = { id, name, tracks: j.tracks.map(t => ({
      library_id: t.library_id || t.id, name: t.name,
      artist: t.artist || "" })) };
    drawEditor();
  } catch (e) { ed.innerHTML = `<div class="dim">${esc(e.message)}</div>`; }
}

function drawEditor() {
  const ed = document.getElementById("ed");
  document.getElementById("ed-name").textContent = editState?.name || "";
  ed.innerHTML = `
    <table><tbody>${editState.tracks.map((t, i) => `
      <tr><td style="width:90px">
        <button class="act" data-mv="up" data-i="${i}" ${i ? "" : "disabled"}>↑</button>
        <button class="act" data-mv="down" data-i="${i}" ${i < editState.tracks.length - 1 ? "" : "disabled"}>↓</button>
      </td><td>${esc(t.name)}<div class="dim small">${esc(t.artist)}</div></td>
      <td style="width:40px"><button class="act danger" data-rm="${i}">✕</button></td></tr>`).join("")}
    </tbody></table>
    <div style="margin-top:10px">
      <button class="act primary" id="save-order">Save order (${editState.tracks.length} tracks)</button>
      <span class="dim small">a save REPLACES the whole playlist on Apple's side</span>
    </div>`;
  ed.querySelector("tbody").addEventListener("click", e => {
    const mv = e.target.closest("[data-mv]");
    const rm = e.target.closest("[data-rm]");
    if (mv) {
      const i = +mv.dataset.i, d = mv.dataset.mv === "up" ? -1 : 1;
      [editState.tracks[i], editState.tracks[i + d]] =
        [editState.tracks[i + d], editState.tracks[i]];
      drawEditor();
    } else if (rm) {
      editState.tracks.splice(+rm.dataset.rm, 1);
      drawEditor();
    }
  });
  ed.querySelector("#save-order").addEventListener("click", async () => {
    if (!confirm(`Replace "${editState.name}" on Apple's side with these ${editState.tracks.length} tracks (in this order)?`)) return;
    await guard(async () => {
      await putJson(`/api/write/playlists/${encodeURIComponent(editState.id)}/tracks`,
        editState.tracks.map(t => t.library_id));
      toast("playlist saved (Apple applies it async)", "ok");
    });
  });
}

// ------------------------------------------------------------- smartlists

const FIELDS = {
  title: ["contains", "equals", "starts", "ends"],
  artist: ["contains", "equals", "starts", "ends"],
  album: ["contains", "equals", "starts", "ends"],
  genre: ["contains"],
  play_count: ["eq", "gt", "gte", "lt", "lte"],
  release_date: ["after", "before"],
  added: ["after", "before"],
  last_played: ["within_days", "older_than_days", "never"],
};

async function showSmartlists() {
  panel().innerHTML = `
    <h2 style="margin-top:0">Smart playlists <span class="dim small">(rules evaluated locally; materialization writes-gated + throttled)</span></h2>
    <div id="sl-list"></div>
    <h2>New smart playlist</h2>
    <div style="display:grid;gap:8px;max-width:640px">
      <input id="sl-name" placeholder="playlist name…">
      <div id="sl-rules"></div>
      <div style="display:flex;gap:8px;align-items:center">
        <select id="sl-sort">
          <option value="added_desc">newest added first</option>
          <option value="added_asc">oldest added first</option>
          <option value="name">name A→Z</option>
          <option value="artist">artist A→Z</option>
          <option value="play_count_desc">most played</option>
          <option value="release_date_desc">newest release</option>
        </select>
        <input id="sl-limit" type="number" min="0" placeholder="limit (0 = no cap)" style="width:140px">
        <button class="act" id="sl-add-rule">+ rule</button>
        <button class="act primary" id="sl-create">Create</button>
      </div>
      <div id="sl-out"></div>
    </div>`;
  const rules = [[]];
  const ruleRow = () => {
    const row = document.createElement("div");
    row.style.cssText = "display:flex;gap:8px;margin-bottom:6px";
    row.innerHTML = `
      <select class="f">${Object.keys(FIELDS).map(f => `<option>${f}</option>`).join("")}</select>
      <select class="o">${FIELDS.title.map(o => `<option>${o}</option>`).join("")}</select>
      <input class="v" placeholder="value…" style="flex:1">
      <button class="act danger" type="button">✕</button>`;
    row.querySelector(".f").addEventListener("change", () => {
      row.querySelector(".o").innerHTML =
        FIELDS[row.querySelector(".f").value].map(o => `<option>${o}</option>`).join("");
    });
    row.querySelector("button").addEventListener("click", () => row.remove());
    return row;
  };
  const ruleBox = panel().querySelector("#sl-rules");
  ruleBox.appendChild(ruleRow());
  panel().querySelector("#sl-add-rule").addEventListener("click",
    () => ruleBox.appendChild(ruleRow()));
  loadSmartlistList();

  panel().querySelector("#sl-create").addEventListener("click", async () => {
    const name = panel().querySelector("#sl-name").value.trim();
    if (!name) { toast("name required", "err"); return; }
    const rules = [...ruleBox.querySelectorAll(":scope > div")].map(row => ({
      field: row.querySelector(".f").value,
      op: row.querySelector(".o").value,
      value: row.querySelector(".v").value,
    })).filter(r => r.value !== "" || r.op === "never");
    const body = { name, rules,
      sort: panel().querySelector("#sl-sort").value,
      limit: +panel().querySelector("#sl-limit").value || 0 };
    await guard(async () => {
      const s = await postJson("/api/smartlists", body);
      toast(`created ${s.id}`, "ok");
      loadSmartlistList();
      return s;
    });
  });
}

async function loadSmartlistList() {
  const box = panel().querySelector("#sl-list");
  try {
    const j = await get("/api/smartlists");
    box.innerHTML = j.items.length ? `<table>
      <tr><th>name</th><th>rules</th><th>last sync</th><th></th></tr>
      ${j.items.map(s => `
        <tr><td>${esc(s.name)}<div class="dim small">${esc(s.id)}</div></td>
        <td class="small dim">${s.rules.map(r => `${esc(r.field)} ${esc(r.op)} ${esc(r.value ?? "")}`).join("<br>")}</td>
        <td class="small dim">${s.last_sync ? `${s.last_count} tracks · ${fmtWhen(s.last_sync)}` : "never"}</td>
        <td style="white-space:nowrap">
          <button class="act" data-prev="${esc(s.id)}">Preview</button>
          <button class="act primary" data-sync="${esc(s.id)}">Sync</button>
          <button class="act danger" data-del="${esc(s.id)}">Delete</button></td></tr>`).join("")}
      </table>`
      : `<div class="dim">none yet — build one below</div>`;
    box.addEventListener("click", async e => {
      const prev = e.target.closest("[data-prev]");
      const sync = e.target.closest("[data-sync]");
      const delBtn = e.target.closest("[data-del]");
      if (prev) {
        try {
          const p = await guard(() => get(`/api/smartlists/${prev.dataset.prev}/preview`));
          panel().querySelector("#sl-out").innerHTML = `
            <h2>Preview — ${esc(p.name)} (${p.count} of ${p.total})</h2>
            <table>${p.items.slice(0, 25).map(r =>
              `<tr><td>${esc(r.name)}<div class="dim small">${esc(r.artist || "")}</div></td></tr>`).join("")}</table>`;
        } catch { /* toast shown */ }
      } else if (sync) {
        sync.disabled = true; sync.textContent = "syncing…";
        try {
          const r = await guard(() =>
            post(`/api/smartlists/${sync.dataset.sync}/refresh`));
          toast(`materialized to ${r.playlist_id} (${r.count} tracks)`, "ok");
          loadSmartlistList();
        } catch { sync.disabled = false; sync.textContent = "Sync"; }
      } else if (delBtn) {
        if (!confirm("Delete this smart-playlist DEFINITION? (Any Apple playlist it materialized stays.)")) return;
        await guard(async () => { await del(`/api/smartlists/${delBtn.dataset.del}`); });
        loadSmartlistList();
      }
    });
  } catch (e) { box.innerHTML = `<div class="dim">${esc(e.message)}</div>`; }
}

// ------------------------------------------------------------- batch heart

async function showHeart() {
  panel().innerHTML = `
    <h2 style="margin-top:0">Batch heart <span class="dim small">(rate sweeps only ADD hearts — they never clear one)</span></h2>
    <div style="display:flex;gap:8px;max-width:640px">
      <input id="h-artist" placeholder="artist (optional)" style="flex:1">
      <input id="h-album" placeholder="album (optional)" style="flex:1">
      <button class="act primary" id="h-plan">Plan</button>
    </div>
    <div id="h-out" style="margin-top:14px"></div>`;
  panel().querySelector("#h-plan").addEventListener("click", async () => {
    const artist = panel().querySelector("#h-artist").value.trim();
    const album = panel().querySelector("#h-album").value.trim();
    if (!artist && !album) { toast("give an artist or an album", "err"); return; }
    const out = panel().querySelector("#h-out");
    out.innerHTML = `<span class="spin"></span>`;
    try {
      const p = await get(`/api/write/sweeps/rate${qs({ artist, album })}`);
      out.innerHTML = `
        <div class="cards">
          <div class="card"><div class="num">${p.would_heart}</div><div class="lbl">would heart</div></div>
          <div class="card"><div class="num">${p.library_size}</div><div class="lbl">library songs scanned</div></div>
        </div>
        <table style="margin-top:10px">${p.songs.slice(0, 20).map(s =>
          `<tr><td>${esc(s.name)}<div class="dim small">${esc(s.artist || "")}</div></td></tr>`).join("")}</table>
        ${p.songs.length > 20 ? `<div class="dim small">…and ${p.songs.length - 20} more</div>` : ""}
        <div style="margin-top:10px">
          <button class="act danger" id="h-run" ${p.would_heart ? "" : "disabled"}>
            Heart ${p.would_heart} song(s)</button>
        </div>`;
      out.querySelector("#h-run").addEventListener("click", async () => {
        if (!confirm(`Heart ${p.would_heart} song(s) in your real library?`)) return;
        await guard(async () => {
          const rep = await post(`/api/write/sweeps/rate${qs({ artist, album, execute: 1 })}`);
          toast(`hearted ${rep.hearted_count} (${rep.already_hearted.length} already had it)`, "ok");
        });
      });
    } catch (e) { out.innerHTML = `<div class="dim">${esc(e.message)}</div>`; }
  });
}

// ------------------------------------------------------------- restore

async function showRestore() {
  panel().innerHTML = `
    <h2 style="margin-top:0">Restore <span class="dim small">(rebuild playlists from a /api/library/export file — dry-run first)</span></h2>
    <p class="dim small">Grab a fresh export first if you don't have one:
      <a class="dim" href="#" id="dl-export">download /api/library/export</a> (slow — a full walk).</p>
    <input type="file" id="r-file" accept=".json,application/json" style="max-width:420px">
    <div id="r-out" style="margin-top:14px"></div>`;
  panel().querySelector("#dl-export").addEventListener("click", async e => {
    e.preventDefault();
    toast("exporting the whole library — this walks everything, be patient");
    await guard(async () => {
      const j = await get("/api/library/export");
      const blob = new Blob([JSON.stringify(j)], { type: "application/json" });
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = "library-export.json";
      a.click();
      toast("export downloaded", "ok");
    });
  });
  panel().querySelector("#r-file").addEventListener("change", async e => {
    const file = e.target.files[0];
    if (!file) return;
    const out = panel().querySelector("#r-out");
    out.innerHTML = `<span class="spin"></span>`;
    try {
      const source = JSON.parse(await file.text());
      const plan = await guard(() => postJson(`/api/write/restore`, source));
      out.innerHTML = `
        <table><tr><th>playlist</th><th>mode</th><th>tracks</th><th>unmatched</th></tr>
        ${plan.playlists.map(p => `
          <tr><td>${esc(p.name)}</td><td><span class="pill ${p.mode === "create" ? "warn" : "ok"}">${esc(p.mode)}</span></td>
          <td>${p.track_count}</td><td>${p.unmatched.length}</td></tr>`).join("")}</table>
        <div style="margin-top:10px">
          <button class="act danger" id="r-run">Execute restore</button>
          <span class="dim small">${plan.totals ? JSON.stringify(plan.totals) : ""}</span>
        </div>`;
      out.querySelector("#r-run").addEventListener("click", async () => {
        if (!confirm("Execute the restore? Missing playlists get created, tracks get added, Apple applies async.")) return;
        await guard(async () => {
          const rep = await postJson(`/api/write/restore${qs({ execute: 1 })}`,
            source);
          toast(`restore done — created ${(rep.report?.created || []).length}, unmatched ${rep.report?.unmatched_total ?? "?"}`, "ok");
        });
      });
    } catch (err) { out.innerHTML = `<div class="dim">${esc(err.message)}</div>`; }
  });
}

showPlaylists();
