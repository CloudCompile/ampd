import { get, post, qs, guard, toast, spinner, render, initHeader,
         fmtWhen, esc } from "./common.js";

initHeader("Ledger");
let statsWindow = "all";
let recentOffset = 0;

// ------------------------------------------------------------- stats

async function loadStats() {
  const cards = document.getElementById("stat-cards");
  spinner(cards);
  try {
    const [stats, series] = await Promise.all([
      get(`/api/history/stats${qs({ window: statsWindow, limit: 10 })}`),
      get("/api/history/stats/series" + qs({ days: 30 })),
    ]);
    drawCards(stats);
    drawChart(series.series);
    drawTops(stats);
  } catch (e) {
    cards.innerHTML = `<div class="dim">stats need the local store — ${
      esc(e.message || "TONEARM_STORE=1")}</div>`;
    document.getElementById("chart").innerHTML = "";
    document.getElementById("top-tracks").innerHTML = "";
    document.getElementById("top-artists").innerHTML = "";
  }
}

function drawCards(stats) {
  const top = stats.top_tracks[0];
  const artist = stats.top_artists[0];
  document.getElementById("stat-cards").innerHTML = `
    <div class="card"><div class="num">${stats.total_plays}</div>
      <div class="lbl">plays ${statsWindow === "all" ? "all time" : statsWindow}</div></div>
    <div class="card"><div class="num" style="font-size:16px">${top ? esc(top.title) : "—"}</div>
      <div class="lbl">top track${top ? ` · ${esc(top.artist || "")} · ${top.plays} plays` : ""}</div></div>
    <div class="card"><div class="num" style="font-size:16px">${artist ? esc(artist.artist) : "—"}</div>
      <div class="lbl">top artist${artist ? ` · ${artist.plays} plays` : ""}</div></div>`;
}

function drawChart(series) {
  const el = document.getElementById("chart");
  if (!series.length) { el.innerHTML = `<div class="dim">no plays recorded yet</div>`; return; }
  const byDay = Object.fromEntries(series.map(p => [p.day, p.plays]));
  const days = [];
  for (let i = 29; i >= 0; i--) {
    const d = new Date(Date.now() - i * 86400000);
    const key = d.toISOString().slice(0, 10);
    days.push([key, byDay[key] || 0]);
  }
  const max = Math.max(1, ...days.map(d => d[1]));
  const W = 1000, H = 120, bw = W / days.length;
  const bars = days.map(([day, n], i) =>
    `<rect x="${(i * bw + 1).toFixed(1)}" y="${(H - (n / max) * (H - 24)).toFixed(1)}"
       width="${Math.max(1, bw - 2).toFixed(1)}" height="${Math.max(n ? 2 : 0, (n / max) * (H - 24)).toFixed(1)}">
       <title>${day}: ${n} plays</title></rect>`).join("");
  const labels = days.map(([day], i) => i % 5 === 0
    ? `<text x="${(i * bw).toFixed(0)}" y="${H - 6}">${day.slice(5)}</text>` : "").join("");
  el.innerHTML = `<svg class="chart" viewBox="0 0 ${W} ${H}" width="100%" height="120" preserveAspectRatio="none">
    ${bars}${labels}</svg>
    <div class="dim small">peak ${max} plays/day</div>`;
}

function drawTops(stats) {
  document.getElementById("top-tracks").innerHTML =
    `<tr><th>#</th><th>track</th><th>plays</th></tr>` +
    (stats.top_tracks.map((t, i) =>
      `<tr><td class="dim">${i + 1}</td><td>${esc(t.title)}<div class="dim small">${esc(t.artist || "")}</div></td>
       <td>${t.plays}</td></tr>`).join("") ||
     `<tr><td colspan="3" class="dim">nothing yet</td></tr>`);
  document.getElementById("top-artists").innerHTML =
    `<tr><th>#</th><th>artist</th><th>plays</th></tr>` +
    (stats.top_artists.map((a, i) =>
      `<tr><td class="dim">${i + 1}</td><td>${esc(a.artist)}</td>
       <td>${a.plays}</td></tr>`).join("") ||
     `<tr><td colspan="3" class="dim">nothing yet</td></tr>`);
}

// ------------------------------------------------------------- recent

async function loadRecent(reset = true) {
  if (reset) { recentOffset = 0; }
  const table = document.getElementById("recent");
  if (reset) table.innerHTML = `<tr><td class="dim"><span class="spin"></span></td></tr>`;
  try {
    const page = await get(`/api/history/recently-played${qs({
      limit: 50, offset: recentOffset })}`);
    const rows = page.items.map(r =>
      `<tr><td>${esc(r.title)}<div class="dim small">${esc(r.artist || "")} · ${esc(r.album || "")}</div></td>
       <td style="white-space:nowrap" class="dim">${fmtWhen(r.played_at)}</td></tr>`).join("");
    if (reset) {
      table.innerHTML = page.items.length
        ? `<tr><th>track</th><th>played</th></tr>` + rows
        : `<tr><td class="dim">the archive starts when TONEARM_STORE=1 was first enabled — nothing yet</td></tr>`;
    } else {
      table.insertAdjacentHTML("beforeend", rows);
    }
    recentOffset = page.next_offset;
    document.getElementById("more-recent").hidden = page.next_offset === null;
  } catch (e) {
    table.innerHTML = `<tr><td class="dim">${esc(e.message)}</td></tr>`;
    document.getElementById("more-recent").hidden = true;
  }
}

// ------------------------------------------------------------- sweeps

async function loadSweeps() {
  const digestBox = document.getElementById("digest-cards");
  spinner(digestBox);
  try {
    const d = await get("/api/write/sweeps/digest");
    digestBox.innerHTML = `
      <div class="card"><div class="num">${d.library_size}</div><div class="lbl">library songs</div></div>
      <div class="card"><div class="num">${d.duplicate_groups}</div><div class="lbl">duplicate groups</div></div>
      <div class="card"><div class="num">${d.removable_rows}</div><div class="lbl">removable rows</div></div>
      <div class="card"><div class="num">${d.never_played}</div><div class="lbl">never played</div></div>`;
    loadDedupe(d);
    loadNeverPlayed(d);
  } catch (e) {
    digestBox.innerHTML = `<div class="dim">digest unavailable — ${esc(e.message)}</div>`;
  }
}

async function loadDedupe(digest) {
  const box = document.getElementById("dedupe");
  if (!digest.duplicate_groups) {
    box.innerHTML = `<h2>Duplicates</h2><div class="dim">none — clean</div>`;
    return;
  }
  box.innerHTML = `<h2>Duplicates — ${digest.duplicate_groups} group(s),
    ${digest.removable_rows} removable</h2>
    <table>${digest.sample_duplicates.map(g =>
      `<tr>${g.map(r => `<td>${esc(r.name)}<div class="dim small">${esc(r.artist || "")} · ${esc(r.album || "")}</div></td>`).join("")}</tr>`).join("")}
    </table>
    <div style="margin-top:10px"><button class="act danger" id="dedupe-run">
      Remove all-but-first (${digest.removable_rows} rows)</button>
      <span class="dim small" id="dedupe-note">dry-run shows the first ${digest.sample_duplicates.length} group(s)</span></div>`;
  document.getElementById("dedupe-run").addEventListener("click", async () => {
    if (!confirm(`Remove ${digest.removable_rows} duplicate library row(s) from your REAL Apple Music library? This cannot be undone.`)) return;
    if (!confirm("Last check — the first row of each group is kept, the rest are deleted for good. Proceed?")) return;
    await guard(async () => {
      const rep = await post(`/api/write/sweeps/dedupe${qs({ execute: 1 })}`);
      toast(`removed ${rep.removed_count} duplicate row(s)`, "ok");
      loadSweeps();
    });
  });
}

async function loadNeverPlayed(digest) {
  const box = document.getElementById("never-played");
  if (!digest.never_played) {
    box.innerHTML = `<h2>Never played</h2><div class="dim">none — everything's been played</div>`;
    return;
  }
  box.innerHTML = `<h2>Never played — ${digest.never_played} song(s)</h2>
    <table>${digest.sample_never_played.map(r =>
      `<tr><td>${esc(r.name)}<div class="dim small">${esc(r.artist || "")} · ${esc(r.album || "")}</div></td></tr>`).join("")}</table>
    ${digest.never_played > digest.sample_never_played.length
      ? `<div class="dim small">showing the first ${digest.sample_never_played.length}</div>` : ""}`;
}

// ------------------------------------------------------------- wiring

document.getElementById("windows").addEventListener("click", e => {
  const b = e.target.closest("button");
  if (!b) return;
  statsWindow = b.dataset.w;
  for (const x of document.querySelectorAll("#windows button"))
    x.classList.toggle("active", x === b);
  loadStats();
});
document.getElementById("more-recent")
  .addEventListener("click", () => loadRecent(false));

loadStats();
loadRecent();
loadSweeps();
