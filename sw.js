// sw.js — Service Worker Grain d'Or
// Met en cache l'application (page, moteur de calcul, base de données des
// cultures) dès la première visite, pour qu'elle marche ensuite même sans
// aucune connexion internet.

const CACHE_NAME = 'grain-dor-v1';
const ASSETS = [
  './',
  './index.html',
  './reasoning-engine.js',
  './cultures_37.json',
  './manifest.json',
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(ASSETS))
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((names) =>
      Promise.all(names.filter((n) => n !== CACHE_NAME).map((n) => caches.delete(n)))
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  event.respondWith(
    caches.match(event.request).then((cached) => {
      if (cached) return cached;
      return fetch(event.request).then((response) => {
        // Met aussi en cache les nouvelles requêtes réussies (mêmes origines).
        if (response.ok && event.request.url.startsWith(self.location.origin)) {
          const clone = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone));
        }
        return response;
      }).catch(() => cached);
    })
  );
});

