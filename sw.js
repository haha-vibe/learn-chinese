/* Learn Chinese apps — offline service worker.
 *
 * Why this exists: the apps have no runtime dependencies, but when hosted on
 * GitHub Pages the browser must still fetch the HTML/JSON shells over the
 * network on every visit. With no network, there is nothing to load. This
 * worker caches the page shells and poem JSON so the apps open offline after
 * one online visit.
 *
 * Strategy: network-first for same-origin GET requests — when online, always
 * fetch the latest copy and refresh the cache, so the author's updates show
 * immediately (no stale-load lag). When offline or the network fails, serve
 * the last cached copy. Cross-origin requests (e.g. speech-synthesis voices,
 * YouTube, EDB audio) are left untouched.
 *
 * Bump CACHE when you want to force-drop old caches.
 */
const CACHE = 'learn-chinese-v7';
const CORE_ASSETS = [
  './learnchinese.html',
  './poems.html',
  './hanzi/tps-dictionary.json',
  './hanzi/cedict-supplement.json',
  './poems/poems-g1.json',
  './poems/poems-g2.json',
  './poems/poems-g3.json',
  './poems/poems-g4.json',
  './poems/poems-g5.json',
  './poems/poems-g6.json',
  './poems/poems-media.json',
  './poems/categories.json',
  './poems/rhetoric.json',
];

self.addEventListener('install', (e) => {
  // Precache shells/data, but do NOT skipWaiting here: let the new worker wait
  // so the open page can detect it and prompt the user to reload. The page asks
  // us to activate by posting {type:'SKIP_WAITING'} (see the message handler).
  e.waitUntil((async () => {
    const cache = await caches.open(CACHE);
    await cache.addAll(CORE_ASSETS);
  })());
});

self.addEventListener('message', (e) => {
  const data = e.data || {};
  if (data.type === 'SKIP_WAITING') { self.skipWaiting(); return; }
  if (data.type === 'CHECK_UPDATES') { e.waitUntil(checkCoreUpdates()); return; }
});

// Compare each cached CORE_ASSET against the server by ETag/Last-Modified.
// Read-only (never mutates the cache) — the user's reload does the refresh via
// the network-first fetch handler. Notifies all clients if anything changed.
async function checkCoreUpdates() {
  const cache = await caches.open(CACHE);
  const tagOf = (res) => res && (res.headers.get('ETag') || res.headers.get('Last-Modified'));
  const changed = [];
  await Promise.all(CORE_ASSETS.map(async (url) => {
    try {
      const cached = await cache.match(url);
      const oldTag = tagOf(cached);
      if (!oldTag) return;                       // nothing cached yet, or no validator → skip
      const head = await fetch(url, { method: 'HEAD', cache: 'no-store' });
      if (!head || !head.ok) return;
      const newTag = tagOf(head);
      if (newTag && newTag !== oldTag) changed.push(url);
    } catch (_) { /* offline / network error → ignore */ }
  }));
  if (changed.length) {
    const clients = await self.clients.matchAll({ includeUncontrolled: true });
    clients.forEach((c) => c.postMessage({ type: 'DATA_CHANGED', files: changed }));
  }
}

self.addEventListener('activate', (e) => {
  e.waitUntil((async () => {
    const keys = await caches.keys();
    await Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)));
    await self.clients.claim();
  })());
});

self.addEventListener('fetch', (e) => {
  const req = e.request;
  if (req.method !== 'GET') return;
  if (new URL(req.url).origin !== self.location.origin) return;

  e.respondWith((async () => {
    const cache = await caches.open(CACHE);
    try {
      // Network-first: fetch fresh, and refresh the cache when it succeeds.
      const res = await fetch(req);
      if (res && res.ok) cache.put(req, res.clone());
      return res;
    } catch (_) {
      // Offline / network error: fall back to the last cached copy.
      const cached = await cache.match(req);
      return cached || Response.error();
    }
  })());
});
