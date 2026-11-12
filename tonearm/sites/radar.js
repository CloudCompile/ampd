import { get, post, guard, toast, spinner, initHeader, fmtDate, fmtWhen,
         esc } from "./common.js";

initHeader("Radar");
const panel = () => document.getElementById("panel");

document.getElementById("tabs").addEventListener("click", e => {
  const b = e.target.closest("button");
  if (!b) return;
  for (const x of document.querySelectorAll("#tabs button"))
    x.classList.toggle("active", x === b);
  ({ recent: showRecent, foryou: showForYou, rotation: showRotation,
     watcher: showWatcher, lookup: showLookup })[b.dataset.t]();
});

const art = (r, size = 48) => {
  const url = (r.artwork || "").replace("{w}", String(size * 2))
    .replace("{h}", String(size * 2));
  return url ? `<img src="${esc(url)}" width="${size}" height="${size}"
    style="border-radius:8px;object-fit:cover;flex:none"
    onerror="this.style.visibility='hidden'">`
    : `<div style="width:${size}px;height:${size}px;border-radius:8px;
       background:var(--panel2);flex:none;display:grid;place-items:center;
       color:var(--dim)">♫</div>`;
};

// ------------------------------------------------------------- recent

async function showRecent() {
  panel().innerHTML = `<h2 style="margin-top:0">Recently added to your library</h2><div id="out"><span class="spin"></span></div>`;
  try {
    const j = await get("/api/library/recently-added?limit=100");
    panel().querySelector("#out").innerHTML = j.items.length
      ? `<table><tr><th></th><th>name</th><th>artist</th><th>album</th><th>kind</th></tr>${j.items.map(r =>
        `<tr><td>${art(r)}</td><td>${esc(r.name)}<div class="dim small">${r.release_date ? "released " + fmtDate(r.release_date) : ""}</div></td>
         <td>${esc(r.artist || "")}</td><td>${esc(r.album || "")}</td>
         <td><span class="pill">${esc((r.type || "").replace("library-", ""))}</span></td></tr>`).join("")}</table>`
      : `<div class="dim">nothing added yet</div>`;
  } catch (e) { panel().querySelector("#out").innerHTML = `<div class="dim">${esc(e.message)}</div>`; }
}

// ------------------------------------------------------------- for you

async function showForYou() {
  panel().innerHTML = `<h2 style="margin-top:0">Apple's picks for you</h2><div id="out"><span class="spin"></span></div>`;
  const out = panel().querySelector("#out");
  try {
    const [recs, mfy] = await Promise.all([
      get("/api/personal/recommendations").catch(() => ({ groups: [] })),
      get("/api/personal/made-for-you").catch(() => ({ playlists: [] })),
    ]);
    const mixRow = p => `<tr><td>${art(p)}</td><td>${esc(p.name)}
      <div class="dim small">${esc((p.attributes || {}).playlistType || "mix")}</div></td></tr>`;
    out.innerHTML = (mfy.playlists || []).map(p =>
      `<h2>Made for you</h2><table>${mixRow(p)}</table>`).join("") +
      (recs.groups || []).map(g =>
        `<h2>${esc(g.title || "Recommended")}</h2>
         ${g.reason ? `<div class="dim small" style="margin-bottom:8px">${esc(g.reason)}</div>` : ""}
         <table>${g.items.map(r =>
           `<tr><td>${art(r)}</td><td>${esc(r.name)}<div class="dim small">${esc(r.artist || "")}</div></td></tr>`).join("")}</table>`).join("") ||
      `<div class="dim">nothing recommended right now</div>`;
  } catch (e) { out.innerHTML = `<div class="dim">${esc(e.message)}</div>`; }
}

// ------------------------------------------------------------- rotation

async function showRotation() {
  panel().innerHTML = `<h2 style="margin-top:0">In heavy rotation</h2><div id="out"><span class="spin"></span></div>`;
  try {
    const j = await get("/api/personal/heavy-rotation");
    panel().querySelector("#out").innerHTML = j.items.length
      ? `<table>${j.items.map(r =>
          `<tr><td>${art(r)}</td><td>${esc(r.name)}<div class="dim small">${esc(r.artist || "")}</div></td></tr>`).join("")}</table>`
      : `<div class="dim">nothing in rotation</div>`;
  } catch (e) { panel().querySelector("#out").innerHTML = `<div class="dim">${esc(e.message)}</div>`; }
}

// ------------------------------------------------------------- watcher

async function showWatcher() {
  panel().innerHTML = `<h2 style="margin-top:0">Release watcher</h2><div id="out"><span class="spin"></span></div>`;
  let info;
  try { info = await get("/api/watcher"); }
  catch (e) {
    panel().querySelector("#out").innerHTML =
      `<div class="dim">${esc(e.message || e)}</div>` +
      (e.code === "watcher_disabled"
        ? `<div class="dim small">arm it with <code>TONEARM_WATCHER=1</code> — and see the verify-live note in the README before trusting the mapping</div>`
        : "");
    return;
  }
  const rows = info.artists.map(a => `
    <tr><td>${esc(a.artist_name || a.artist_id)}
        <div class="dim small">${esc(a.artist_id)}</div></td>
    <td>${a.catalog_artist_id
      ? `<span class="pill ok">mapped</span><div class="dim small">${esc(a.catalog_artist_name || "")}</div>`
      : `<span class="pill warn">unmapped</span>`}</td>
    <td>${a.last_album_id
      ? `${esc(a.last_album_name || a.last_album_id)}
         <div class="dim small">${fmtDate(a.last_release_date)}</div>`
      : `<span class="dim">baseline pending</span>`}</td></tr>`).join("");
  panel().querySelector("#out").innerHTML = `
    <div class="cards">
      <div class="card"><div class="num">${info.watched}</div><div class="lbl">watched</div></div>
      <div class="card"><div class="num">${info.mapped}</div><div class="lbl">mapped to catalog</div></div>
      <div class="card"><div class="num">${info.unmapped}</div><div class="lbl">unmapped</div></div>
      <div class="card"><div class="num">${info.auto_add_active ? "on" : "off"}</div>
        <div class="lbl">auto-add${info.auto_playlist ? " → " + esc(info.auto_playlist) : ""}</div></div>
    </div>
    <div style="margin:12px 0">
      <button class="act primary" id="run-pass">Run a pass now</button>
      <span class="dim small">daily interval ${Math.round(info.interval / 3600)}h ·
        ${info.last_pass ? `last pass checked ${info.last_pass.checked}, ${info.last_pass.new_releases} new` : "no pass yet"}</span>
    </div>
    ${rows ? `<table><tr><th>artist</th><th>mapping</th><th>newest release seen</th></tr>${rows}</table>`
           : `<div class="dim">no artists watched yet — run a pass (the first one is a silent baseline)</div>`}
    <p class="dim small">the artist→catalog mapping is strict name search — an
    unmapped artist is data, not an error; eyeball these against your real
    account (this page is the verify-live gate).</p>`;
  panel().querySelector("#run-pass").addEventListener("click", async () => {
    const btn = panel().querySelector("#run-pass");
    btn.disabled = true; btn.textContent = "running…";
    try {
      const s = await guard(() => post("/api/watcher/refresh"));
      toast(`pass done: ${s.checked} checked, ${s.new_releases} new release(s)`, "ok");
    } catch { /* toast already shown */ }
    showWatcher();
  });
}

// ------------------------------------------------------------- lookup

async function showLookup() {
  panel().innerHTML = `
    <h2 style="margin-top:0">Artist lookup — catalog vs your library</h2>
    <div style="display:flex;gap:8px">
      <input id="who" placeholder="artist name…" style="flex:1">
      <button class="act primary" id="go">Look up</button>
    </div>
    <div id="out" style="margin-top:14px"></div>`;
  const run = async () => {
    const term = panel().querySelector("#who").value.trim();
    if (!term) return;
    const out = panel().querySelector("#out");
    spinner(out);
    try {
      const [cats, mine] = await Promise.all([
        get(`/api/catalog/search${qs({ term, types: "artists", limit: 5 })}`),
        get(`/api/library/search${qs({ term, limit: 25 })}`),
      ]);
      const libAlbums = new Set((mine.albums || []).map(a =>
        (a.name || "").casefold()));
      const hits = cats.artists || [];
      if (!hits.length) { out.innerHTML = `<div class="dim">no catalog artist matched “${esc(term)}”</div>`; return; }
      out.innerHTML = hits.map(a => `
        <section style="margin-bottom:14px">
          <h2 style="margin-top:0">${esc(a.name)} <span class="dim small">${esc(a.id)}</span></h2>
          <div id="alb-${esc(a.id)}"><span class="spin"></span></div>
        </section>`).join("");
      for (const a of hits) loadAlbums(a, libAlbums);
    } catch (e) { out.innerHTML = `<div class="dim">${esc(e.message)}</div>`; }
  };
  panel().querySelector("#go").addEventListener("click", run);
  panel().querySelector("#who").addEventListener("keydown",
    e => { if (e.key === "Enter") run(); });
}

async function loadAlbums(artist, libAlbums) {
  const box = document.getElementById(`alb-${CSS.escape(artist.id)}`);
  try {
    const j = await get(`/api/catalog/artists/${encodeURIComponent(artist.id)}/albums?limit=20`);
    box.innerHTML = j.items.length
      ? `<table>${j.items.map(al => {
          const owned = libAlbums.has((al.name || "").casefold());
          return `<tr><td>${art(al)}</td>
            <td>${esc(al.name)}<div class="dim small">${fmtDate(al.release_date)}</div></td>
            <td>${owned ? `<span class="pill ok">in library</span>`
              : `<button class="act" data-add="${esc(al.id)}">Add album</button>`}</td></tr>`;
        }).join("")}</table>`
      : `<div class="dim">no albums found</div>`;
    box.addEventListener("click", async e => {
      const b = e.target.closest("[data-add]");
      if (!b) return;
      b.disabled = true; b.textContent = "adding…";
      try {
        await guard(() => postJson("/api/write/library/add-albums", [b.dataset.add]));
        toast("added (Apple applies it async — check your library in a moment)", "ok");
        b.textContent = "added ✓";
      } catch { b.disabled = false; b.textContent = "Add album"; }
    });
  } catch (e) { box.innerHTML = `<div class="dim">${esc(e.message)}</div>`; }
}

showRecent();
