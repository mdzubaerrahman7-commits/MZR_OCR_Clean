// Minimal service worker. Its only two jobs are:
//  1. Make the app installable (browsers require a fetch handler to consider a page
//     an installable PWA).
//  2. Show a friendly offline page instead of a browser error when navigation fails
//     because the connection dropped mid-session.
//
// It deliberately does NOT cache API responses, JS/CSS bundles, or RSC data —
// this is an audit tool; serving a stale duty/demand figure or a stale build from
// cache would be a correctness bug, not a convenience. Every request other than
// top-level navigation goes straight to the network, uncached.

const CACHE_NAME = "bondaudit-shell-v1";
const OFFLINE_URL = "/offline.html";

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll([OFFLINE_URL])).then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) => Promise.all(keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  if (event.request.mode !== "navigate") {
    return; // let every non-navigation request (API calls, assets, data) hit the network normally
  }

  event.respondWith(
    fetch(event.request).catch(() => caches.match(OFFLINE_URL))
  );
});
