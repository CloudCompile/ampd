// Library browse (#85): four tabs, one VList each, paginated by next_offset.
// Rows play on click (song: play-song; collection: play-collection).
import { get, post } from "../api.js";
import { VList } from "../vlist.js";
import { esc } from "../util.js";

const el = document.getElementById("list");
const lists = {};

function rowHtml(item) {
  const sub = [item.artist, item.album].filter(Boolean).join(" — ");
  const badge = item.play_count != null ? `${item.play_count} plays` :
                (item.type || "").replace(/^library-/, "");
  return `<div class="t"><b>${esc(item.name)}</b>` +
         `<span>${esc(sub)}</span></div><span class="badge">${esc(badge)}</span>`;
}

async function loader(resource) {
  return async (offset, limit) => {
    const page = await get(`/api/library/${resource}`, { offset, limit });
    return { items: page.items, next_offset: page.next_offset };
  };
}

function ensure(tab) {
  if (!lists[tab]) {
    lists[tab] = new VList(el, rowHtml);
    el.addEventListener("click", (e) => {
      const row = e.target.closest(".row");
      if (!row) return;
      const item = lists[tab].rows[+row.dataset.i];
      if (!item) return;
      if (tab === "songs" && item.catalog_id)
        post(`/api/playback/play-song/${item.catalog_id}`);
      else if (tab !== "songs" && item.id)
        post("/api/playback/play-collection",
             { kind: tab.slice(0, -1), resource_id: item.id });
    });
  }
  return lists[tab];
}

export async function show(tab) {
  el.hidden = false;
  document.getElementById("searchout").hidden = true;
  const list = ensure(tab);
  el.className = "list";
  await list.setLoader(loader(tab));
}

export function markNow(id) {
  for (const l of Object.values(lists)) l.markNow(id);
}
