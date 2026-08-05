// A+ DESK service worker.
//
// This caches the application SHELL only — never market data. The desk's core
// honesty constraint is that it shows an error rather than stale numbers, and a
// service worker is the easiest place to break that by accident: a cache-first
// rule over the data worker would happily serve last night's prices as though
// they were live, with the page none the wiser.
//
// So: shell is cache-first (instant launch, survives being offline), and the
// data worker is network-ONLY with no fallback. Offline, the shell loads and the
// page shows its existing "data worker unreachable" error. That is the correct
// behaviour for a trading terminal.

const SHELL_CACHE = "aplusdesk-shell-v1";
const SHELL = [
  ".",
  "index.html",
  "vendor/lightweight-charts.js",
  "manifest.json",
  "icons/icon-192.png",
  "icons/icon-512.png",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(SHELL_CACHE)
      // Individual addAll failures would abort the whole install, so tolerate a
      // missing optional asset rather than shipping a worker that never activates.
      .then((c) => Promise.allSettled(SHELL.map((u) => c.add(new Request(u, { cache: "reload" })))))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== SHELL_CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET") return;

  const url = new URL(req.url);

  // Market data and context: network only. Never cached, never served stale.
  if (url.hostname.endsWith(".workers.dev")) return;

  // Cross-origin anything else: leave it alone.
  if (url.origin !== self.location.origin) return;

  event.respondWith(
    caches.match(req).then((hit) => {
      if (hit) {
        // Refresh in the background so the next launch has the new shell.
        event.waitUntil(
          fetch(req).then((res) => {
            if (res && res.ok) return caches.open(SHELL_CACHE).then((c) => c.put(req, res));
          }).catch(() => {})
        );
        return hit;
      }
      return fetch(req).then((res) => {
        if (res && res.ok && res.type === "basic") {
          const copy = res.clone();
          event.waitUntil(caches.open(SHELL_CACHE).then((c) => c.put(req, copy)));
        }
        return res;
      });
    })
  );
});
