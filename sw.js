// Kurir-Q service worker — dipakai di web (Cloudflare Pages) dan APK (Capacitor).
// Strategi: shell app = stale-while-revalidate, tile OSM = cache-first.
const SHELL = 'kurir-q-shell-v2';
const TILES = 'kurir-q-tiles-v1'; // nama sama dengan downloader di index.html
const SHELL_FILES = [
  './', './index.html',
  './lib/leaflet.js', './lib/leaflet.css',
  './lib/images/marker-icon.png', './lib/images/marker-icon-2x.png',
  './lib/images/marker-shadow.png', './lib/images/layers.png', './lib/images/layers-2x.png'
];
const TILE_RE = /^https:\/\/[abc]\.tile\.openstreetmap\.org\/(\d+\/\d+\/\d+\.png)/;

self.addEventListener('install', (e) => {
  e.waitUntil(
    caches.open(SHELL)
      .then((c) => Promise.all(SHELL_FILES.map((u) => c.add(u).catch(() => {}))))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys()
      .then((names) => Promise.all(names
        .filter((n) => n !== SHELL && !n.startsWith('kurir-q-tiles'))
        .map((n) => caches.delete(n))))
      .then(() => self.clients.claim())
  );
});

// Downloader memilih subdomain a/b/c berdasarkan (x+y)%3, sedangkan Leaflet
// memilih acak — jadi cek ketiganya supaya tile hasil unduhan terpakai.
async function tileFromCache(cache, path) {
  for (const s of ['a', 'b', 'c']) {
    const hit = await cache.match(`https://${s}.tile.openstreetmap.org/${path}`, { ignoreVary: true });
    if (hit) return hit;
  }
  return null;
}

async function handleTile(url, path) {
  const cache = await caches.open(TILES);
  const hit = await tileFromCache(cache, path);
  if (hit) return hit;
  try {
    // mode cors: respons terbaca & ukurannya jujur (opaque dihitung ~7 MB/tile oleh browser)
    const resp = await fetch(url, { mode: 'cors' });
    if (resp.ok) cache.put(url, resp.clone());
    return resp;
  } catch (err) {
    return new Response('', { status: 404 });
  }
}

async function handleShell(request) {
  const cache = await caches.open(SHELL);
  const cached = await cache.match(request, { ignoreSearch: true });
  const network = fetch(request)
    .then((resp) => { if (resp && resp.ok) cache.put(request, resp.clone()); return resp; })
    .catch(() => null);
  if (cached) { network.catch(() => {}); return cached; }
  const resp = await network;
  if (resp) return resp;
  if (request.mode === 'navigate') {
    const fallback = await cache.match('./index.html');
    if (fallback) return fallback;
  }
  return new Response('Offline', { status: 503 });
}

self.addEventListener('fetch', (e) => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const m = req.url.match(TILE_RE);
  if (m) { e.respondWith(handleTile(req.url, m[1])); return; }
  if (new URL(req.url).origin === self.location.origin) e.respondWith(handleShell(req));
  // selain itu (API routing, WhatsApp, dll) lewat jaringan biasa
});
