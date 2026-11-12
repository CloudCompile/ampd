// tonearm/sites/common.js — shared plumbing for /ledger /radar /bench.
// Auth dialect is the PWA's: pages load keylessly, the key (if the server
// demands one) rides Authorization: Bearer and lives in localStorage.
export class ApiError extends Error {
  constructor(status, body) {
    const err = (body && body.error) || {};
    super(err.hint || err.code || `HTTP ${status}`);
    this.status = status;
    this.code = err.code;
    this.hint = err.hint;
  }
}

const K = { base: "tonearm_site_base", key: "tonearm_site_key" };

export const settings = {
  get base() { return localStorage.getItem(K.base) || ""; },
  set base(v) { localStorage.setItem(K.base, v.trim().replace(/\/+$/, "")); },
  get key() { return localStorage.getItem(K.key) || ""; },
  set key(v) { localStorage.setItem(K.key, v.trim()); },
};

export async function api(path, opts = {}) {
  const headers = { ...(opts.headers || {}) };
  if (settings.key) headers["Authorization"] = `Bearer ${settings.key}`;
  let res;
  try {
    res = await fetch(settings.base + path, { ...opts, headers });
  } catch (e) {
    throw new ApiError(0, { error: { code: "unreachable",
      hint: `could not reach ${settings.base || "this origin"} — check the base URL in settings` } });
  }
  let body = {};
  try { body = await res.json(); } catch { /* empty body (204) */ }
  if (!res.ok) throw new ApiError(res.status, body);
  return body;
}

export const get = (path) => api(path);
export const post = (path) => api(path, { method: "POST" });
export const postJson = (path, body) => api(path, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});
export const putJson = (path, body) => api(path, {
  method: "PUT",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});
export const del = (path) => api(path, { method: "DELETE" });

/** Scalar params go in the query string (house contract: scalars are
 * query, lists are bare JSON arrays). */
export function qs(params) {
  const u = new URLSearchParams();
  for (const [k, v] of Object.entries(params || {}))
    if (v !== undefined && v !== null && v !== "") u.set(k, v);
  const s = u.toString();
  return s ? `?${s}` : "";
}

// ------------------------------------------------------------------ dom

export function toast(msg, kind = "") {
  let host = document.getElementById("toasts");
  if (!host) { host = document.createElement("div"); host.id = "toasts";
    document.body.appendChild(host); }
  const t = document.createElement("div");
  t.className = `toast ${kind}`;
  t.textContent = msg;
  host.appendChild(t);
  setTimeout(() => t.remove(), kind === "err" ? 9000 : 4500);
}

export async function guard(fn, okMsg) {
  try {
    const out = await fn();
    if (okMsg) toast(okMsg, "ok");
    return out;
  } catch (e) {
    if (e instanceof ApiError && e.status === 401) {
      askKey("This server requires an API key.");
    } else {
      toast(e.hint ? `${e.message}` : String(e.message || e), "err");
    }
    throw e;
  }
}

export function askKey(reason) {
  const d = document.createElement("dialog");
  d.innerHTML = `<form method="dialog">
    <p><b>API key needed.</b><br><span class="dim">${reason || ""}</span></p>
    <p><input id="k" type="password" placeholder="TONEARM_API_KEY" style="width:100%"></p>
    <p style="text-align:right"><button class="act primary">Save</button></p>
  </form>`;
  d.addEventListener("close", () => { if (d.querySelector("#k").value)
    settings.key = d.querySelector("#k").value; });
  document.body.appendChild(d);
  d.showModal();
}

export function fmtWhen(ts) {
  if (!ts) return "—";
  const s = typeof ts === "number" ? ts : Date.parse(ts) / 1000;
  if (Number.isNaN(s)) return String(ts);
  const d = new Date(s * 1000);
  return d.toLocaleDateString(undefined,
    { month: "short", day: "numeric" }) + " " +
    d.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" });
}

export function fmtDate(iso) {
  if (!iso) return "—";
  return iso.slice(0, 10);
}

export function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g,
    c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;",
            "'": "&#39;" }[c]));
}

export function render(html) {
  document.querySelector("main").innerHTML = html;
}

export function spinner(target) {
  const el = typeof target === "string" ? document.querySelector(target)
    : target;
  el.innerHTML = `<span class="spin"></span>`;
}

// ------------------------------------------------------------- header

export function initHeader(title) {
  const here = location.pathname;
  const link = (href, label) =>
    `<a href="${href}" class="${here === href ? "active" : ""}">${label}</a>`;
  document.body.insertAdjacentHTML("afterbegin", `
    <header>
      <h1>${esc(title)}</h1>
      <nav>${link("/ledger", "Ledger")}${link("/radar", "Radar")}${link("/bench", "Bench")}</nav>
      <button id="settings-btn">settings</button>
    </header>`);
  const d = document.createElement("dialog");
  d.innerHTML = `<form method="dialog">
    <p><b>tonearm connection</b></p>
    <p>Base URL (blank = this origin)<br>
      <input id="b" style="width:100%" placeholder="http://127.0.0.1:8188"
             value="${esc(settings.base)}"></p>
    <p>API key (only if the server set TONEARM_API_KEY)<br>
      <input id="k" type="password" style="width:100%"
             value="${esc(settings.key)}"></p>
    <p style="text-align:right"><button class="act primary">Save</button></p>
  </form>`;
  d.addEventListener("close", () => {
    settings.base = d.querySelector("#b").value;
    settings.key = d.querySelector("#k").value;
    location.reload();
  });
  document.body.appendChild(d);
  document.getElementById("settings-btn")
    .addEventListener("click", () => d.showModal());
}
