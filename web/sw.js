/* ampd service worker (#90) — cache the SHELL, never the API.
   The shell is precached on install and re-fetched stale-while-revalidate;
   every /api request goes straight to the network (it is live data — an
   audio stream or a playhead snapshot served from cache is a lie). */
const CACHE = "ampd-shell-v1";
const SHELL = ["/", "/app.js", "/styles.css", "/manifest.webmanifest"];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE)
    .then((c) => c.addAll(SHELL))
    .then(() => self.skipWaiting()));
});

self.addEventListener("activate", (e) => {
  e.waitUntil(caches.keys()
    .then((keys) => Promise.all(
      keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
    .then(() => self.clients.claim()));
});

self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  if (url.pathname.startsWith("/api/") || url.pathname.startsWith("/metrics")) {
    return;                                   // NEVER the API — live data only
  }
  if (e.request.method !== "GET" || url.origin !== location.origin) return;

  // shell: cache-first, refresh in the background
  e.respondWith(caches.open(CACHE).then(async (c) => {
    const hit = await c.match(e.request);
    const net = fetch(e.request).then((r) => {
      if (r.ok) c.put(e.request, r.clone());
      return r;
    }).catch(() => hit);
    return hit || net;
  }));
});
