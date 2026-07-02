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
const CACHE = 'learn-chinese-v10';
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
  console.log('[sw] install', CACHE);
  // Precache shells/data, but do NOT skipWaiting here: let the new worker wait
  // so the open page can detect it and prompt the user to reload. The page asks
  // us to activate by posting {type:'SKIP_WAITING'} (see the message handler).
  e.waitUntil((async () => {
    const cache = await caches.open(CACHE);
    await cache.addAll(CORE_ASSETS);
    console.log('[sw] install: precached', CORE_ASSETS.length, 'assets');
  })());
});

self.addEventListener('message', (e) => {
  const data = e.data || {};
  console.log('[sw] message received:', data.type, 'from', e.source && e.source.url);
  if (data.type === 'SKIP_WAITING') { console.log('[sw] skipWaiting()'); self.skipWaiting(); return; }
  if (data.type === 'CHECK_UPDATES') { e.waitUntil(checkCoreUpdates()); return; }
});

// Compare each cached CORE_ASSET against the server by ETag/Last-Modified.
// Never mutates the cache itself — the user's reload does the refresh via the
// network-first fetch handler. Stateless by design: reports every file whose
// live tag differs from the cached one, every time it's asked. Dedup against
// "did I already tell the user about this exact version" is the *page's* job
// (see poems.html), using localStorage — NOT an in-memory SW variable, which
// would get silently wiped whenever the browser terminates the idle worker
// (routine, and far more frequent than the 30-min/tab-focus check interval,
// which is exactly what made the old in-memory-only attempt at this
// re-surface the same already-seen change over and over).
async function checkCoreUpdates() {
  const t0 = Date.now();
  console.log('[sw] checkCoreUpdates: start, cache =', CACHE);
  const cache = await caches.open(CACHE);
  const tagOf = (res) => res && (res.headers.get('ETag') || res.headers.get('Last-Modified'));
  const changed = [];
  await Promise.all(CORE_ASSETS.map(async (url) => {
    try {
      const cached = await cache.match(url);
      const oldTag = tagOf(cached);
      if (!oldTag) { console.log('[sw]  ', url, '-> no cached tag (not yet cached / no validator), skipping'); return; }
      const head = await fetch(url, { method: 'HEAD', cache: 'no-store' });
      if (!head || !head.ok) { console.log('[sw]  ', url, '-> HEAD failed, status', head && head.status); return; }
      const newTag = tagOf(head);
      console.log('[sw]  ', url, { oldTag, newTag });
      if (newTag && newTag !== oldTag) changed.push({ url, tag: newTag });
    } catch (err) { console.log('[sw]  ', url, '-> error (offline?):', err && err.message); }
  }));
  console.log('[sw] checkCoreUpdates: done in', Date.now() - t0, 'ms, changed =', changed);
  if (changed.length) {
    const clients = await self.clients.matchAll({ includeUncontrolled: true });
    console.log('[sw] posting DATA_CHANGED to', clients.length, 'client(s)');
    clients.forEach((c) => c.postMessage({ type: 'DATA_CHANGED', files: changed }));
  }
}

self.addEventListener('activate', (e) => {
  console.log('[sw] activate', CACHE);
  e.waitUntil((async () => {
    const keys = await caches.keys();
    const stale = keys.filter((k) => k !== CACHE);
    if (stale.length) console.log('[sw] activate: dropping stale caches', stale);
    await Promise.all(stale.map((k) => caches.delete(k)));
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
