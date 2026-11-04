const CACHE_NAME = 'py2java-cache-v3';
const urlsToCache = [
  '/static/css/style.css',
  '/static/css/quizzes.css',
  '/static/images/logo-dark.png',
  '/static/images/logo-light.png',
  '/static/js/main.js',
  '/static/js/quizzes.js',
  '/static/js/progress.js',
  '/static/js/search.js',
  '/static/js/roadmap.js'
];

self.addEventListener('install', event => {
  self.skipWaiting();
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(urlsToCache))
  );
});

self.addEventListener('activate', event => {
  const cacheWhitelist = [CACHE_NAME];
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cacheName => {
          if (cacheWhitelist.indexOf(cacheName) === -1) {
            return caches.delete(cacheName);
          }
        })
      );
    }).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', event => {
  if (event.request.method !== 'GET' || !event.request.url.startsWith(self.location.origin)) {
    return;
  }

  const url = new URL(event.request.url);

  // Nunca cachear endpoints de API ni rutas de autenticación/sesión
  if (
    url.pathname.startsWith('/api/') ||
    url.pathname.startsWith('/login') ||
    url.pathname.startsWith('/logout') ||
    url.pathname.startsWith('/register') ||
    url.pathname.startsWith('/recuperar')
  ) {
    return;
  }

  // Estrategia Cache-First con actualización en segundo plano solo para archivos estáticos (/static/)
  if (url.pathname.startsWith('/static/')) {
    event.respondWith(
      caches.match(event.request).then(cachedResponse => {
        const networkFetch = fetch(event.request).then(networkResponse => {
          if (networkResponse && networkResponse.status === 200 && networkResponse.type === 'basic') {
            const responseClone = networkResponse.clone();
            caches.open(CACHE_NAME).then(cache => cache.put(event.request, responseClone));
          }
          return networkResponse;
        }).catch(() => cachedResponse);

        return cachedResponse || networkFetch;
      })
    );
    return;
  }

  // Estrategia Network-First para documentos HTML / navegación
  event.respondWith(
    fetch(event.request).catch(() => caches.match(event.request))
  );
});
