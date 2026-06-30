/* Learn Chinese apps — offline service worker.
 *
 * Why this exists: the apps have no runtime dependencies, but when hosted on
 * GitHub Pages the browser must still fetch the HTML/JSON shells over the
 * network on every visit. With no network, there is nothing to load. This
 * worker caches the page shells and poem JSON so the apps open offline after
 * one online visit.
 *
 * Strategy: stale-while-revalidate for same-origin GET requests — serve the
 * cached copy instantly, then refresh the cache in the background so the
 * author's updates propagate on the next load. Cross-origin requests (e.g.
 * speech-synthesis voices) are left untouched.
 *
 * Bump CACHE when you want to force-drop old caches.
 */
const CACHE = 'learn-chinese-v3';
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
];

self.addEventListener('install', (e) => {
  e.waitUntil((async () => {
    const cache = await caches.open(CACHE);
    await cache.addAll(CORE_ASSETS);
    await self.skipWaiting();
  })());
});

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
    const cached = await cache.match(req);
    const network = fetch(req)
      .then((res) => {
        if (res && res.ok) cache.put(req, res.clone());
        return res;
      })
      .catch(() => null);

    // Cached first (fast, offline-safe); fall back to network on a cold cache.
    return cached || (await network) || Response.error();
  })());
});
