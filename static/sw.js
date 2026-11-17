// RetailPOS Pro — Service Worker v3
// Estrategia: network-first para HTML/API, cache-first para assets y barcodes.

const CACHE_NAME = 'retailpos-v3';
const BARCODE_CACHE = 'retailpos-barcodes-v3';

const APP_SHELL = [
  '/',
  '/static/app.css',
  '/static/app.js',
  '/manifest.json',
  '/static/icons/icon-192.png',
  '/static/icons/icon-512.png',
];

// Instalar: pre-cachear el shell de la app.
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(APP_SHELL))
  );
  self.skipWaiting();
});

// Activar: descartar versiones anteriores.
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys
          .filter((key) => key !== CACHE_NAME && key !== BARCODE_CACHE)
          .map((key) => caches.delete(key))
      )
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', (e) => {
  if (e.request.method !== 'GET') return;

  const url = new URL(e.request.url);
  if (url.origin !== self.location.origin) return;

  // Barcodes SVG: cambian poco, cache-first.
  if (url.pathname.startsWith('/api/barcode-inline/')) {
    e.respondWith(cacheFirst(e.request, BARCODE_CACHE));
    return;
  }

  // Navegación: red primero para entregar mejoras al instante.
  if (e.request.mode === 'navigate') {
    e.respondWith(networkFirst(e.request, CACHE_NAME));
    return;
  }

  // API de datos: red primero; offline degrada a 503 JSON.
  if (url.pathname.startsWith('/api/')) {
    e.respondWith(networkFirst(e.request, CACHE_NAME));
    return;
  }

  // Assets estáticos: cache-first.
  e.respondWith(cacheFirst(e.request, CACHE_NAME));
});

async function networkFirst(request, cacheName) {
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
      status: 503,
      headers: { 'Content-Type': 'application/json; charset=utf-8' },
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
    return new Response(JSON.stringify({ error: 'Sin conexión', offline: true }), {
      status: 503,
      headers: { 'Content-Type': 'application/json; charset=utf-8' },
    });
  }
}

self.addEventListener('message', (event) => {
  if (event.data?.type === 'CLEAR_BARCODE_CACHE') {
    caches.delete(BARCODE_CACHE).then(() => {
      event.ports[0]?.postMessage({ ok: true });
    });
  }
});
