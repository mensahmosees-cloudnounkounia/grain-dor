// sw.js — Service Worker Grain d'Or
// Met en cache l'application (page, moteur de calcul, base de données des
// cultures) dès la première visite, pour qu'elle marche ensuite même sans
// aucune connexion internet.
//
// IMPORTANT : cultures_37.json est servi en "réseau d'abord" (pas cache
// d'abord), pour qu'une mise à jour des données (ex: nouveaux savoirs
// paysans) soit visible dès la prochaine connexion, sans que l'utilisateur
// ait à vider son cache. Le cache ne sert que de secours hors-ligne.

const CACHE_NAME = 'grain-dor-v2';
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
  const url = event.request.url;

  // Données (cultures_37.json) : réseau d'abord, cache seulement si hors-ligne.
  if (url.endsWith('cultures_37.json')) {
    event.respondWith(
      fetch(event.request)
        .then((response) => {
          if (response.ok) {
            const clone = response.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone));
          }
          return response;
        })
        .catch(() => caches.match(event.request))
    );
    return;
  }

  // Reste de l'app (HTML, JS, manifest) : cache d'abord, réseau en secours.
  event.respondWith(
    caches.match(event.request).then((cached) => {
      if (cached) return cached;
      return fetch(event.request).then((response) => {
        if (response.ok && url.startsWith(self.location.origin)) {
          const clone = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone));
        }
        return response;
      }).catch(() => cached);
    })
  );
});
