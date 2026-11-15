// RetailPOS Pro — Service Worker
// Estrategia: Network first → Cache fallback para datos, Cache first para assets

const CACHE_NAME = 'retailpos-v1';
const BARCODE_CACHE = 'retailpos-barcodes-v1';

const APP_SHELL = [
  '/',
  '/static/manifest.json',
];

// Instalar: pre-cachear shell
self.addEventListener('install', (e) => {
  e.waitUntil(
    caches.open(CACHE_NAME).then(cache => cache.addAll(APP_SHELL))
  );
  self.skipWaiting();
});

// Activar: limpiar caches viejos
self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(
        keys.filter(k => k !== CACHE_NAME && k !== BARCODE_CACHE)
            .map(k => caches.delete(k))
      )
    )
  );
  self.clients.claim();
});

// Fetch: lógica de caché por tipo de recurso
self.addEventListener('fetch', (e) => {
  const url = new URL(e.request.url);

  // Barcodes SVG: cache-first (cambian poco)
  if (url.pathname.startsWith('/api/barcode-inline/')) {
    e.respondWith(cacheFirst(e.request, BARCODE_CACHE, 86400)); // 24h
    return;
  }

  // API de datos: network-first (datos frescos)
  if (url.pathname.startsWith('/api/')) {
    e.respondWith(networkFirst(e.request, CACHE_NAME, 300)); // 5min fallback
    return;
  }

  // App shell / static: cache-first
  e.respondWith(cacheFirst(e.request, CACHE_NAME));
});

async function networkFirst(request, cacheName, maxAgeSeconds) {
  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(cacheName);
      cache.put(request, response.clone());
    }
    return response;
  } catch {
    const cached = await caches.match(request);
    if (cached) return cached;
    return new Response(JSON.stringify({ error: 'Sin conexión', offline: true }), {
      headers: { 'Content-Type': 'application/json' }
    });
  }
}

async function cacheFirst(request, cacheName) {
  const cached = await caches.match(request);
  if (cached) return cached;
  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(cacheName);
      cache.put(request, response.clone());
    }
    return response;
  } catch {
    return new Response('Sin conexión', { status: 503 });
  }
}

// Mensaje desde la app para limpiar caché de barcodes
self.addEventListener('message', (e) => {
  if (e.data?.type === 'CLEAR_BARCODE_CACHE') {
    caches.delete(BARCODE_CACHE).then(() => {
      e.ports[0]?.postMessage({ ok: true });
    });
  }
});
