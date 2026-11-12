// API access (#90): the key lives in localStorage and rides EVERYWHERE —
// as ?api_key= (EventSource cannot send headers) and as a Bearer header
// (every fetch). The server accepts either.
const KEY = () => localStorage.getItem("tonearm_key") || "";

export function needsKey() { return !!KEY(); }

function url(path, params = {}) {
  const u = new URL(path, location.origin);
  if (KEY()) u.searchParams.set("api_key", KEY());
  for (const [k, v] of Object.entries(params))
    if (v !== undefined && v !== null) u.searchParams.set(k, v);
  return u.pathname + u.search;
}

export async function get(path, params) {
  const r = await fetch(url(path, params), {
    headers: KEY() ? { Authorization: `Bearer ${KEY()}` } : {},
  });
  if (!r.ok) throw errWithStatus(`${r.status} ${path}`, r.status);
  return r.json();
}

export async function send(path, method, body, params) {
  const r = await fetch(url(path, params), {
    method,
    headers: {
      ...(body ? { "Content-Type": "application/json" } : {}),
      ...(KEY() ? { Authorization: `Bearer ${KEY()}` } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!r.ok) throw errWithStatus(`${r.status} ${method} ${path}`, r.status);
  return r.json().catch(() => ({}));
}

// structured errors (#90 followup): the key prompt must match on the STATUS,
// never on substrings of the message — "404 /api/catalog/songs/6401003/…"
// contains "401" and would open the modal spuriously (real ids hit this too).
function errWithStatus(message, status) {
  const e = new Error(message);
  e.status = status;
  return e;
}

export const post = (p, body) => send(p, "POST", body);
export const put = (p, body) => send(p, "PUT", body);
