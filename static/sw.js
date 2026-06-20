const CACHE_NAME = 'py2java-cache-v1';
const urlsToCache = [
  '/',
  '/static/css/style.css',
  '/static/css/quizzes.css',
  '/static/js/main.js',
  '/static/js/quizzes.js',
  '/static/js/progress.js',
  '/static/js/search.js',
  '/static/js/roadmap.js'
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        return cache.addAll(urlsToCache);
      })
  );
});

self.addEventListener('fetch', event => {
  // Ignorar peticiones POST/PUT/DELETE o fuera del dominio
  if (event.request.method !== 'GET' || !event.request.url.startsWith(self.location.origin)) {
    return;
  }

  // Network first para /api/, Cache first para estáticos
  if (event.request.url.includes('/api/')) {
    event.respondWith(
      fetch(event.request).catch(() => caches.match(event.request))
    );
  } else {
    event.respondWith(
      caches.match(event.request)
        .then(response => {
          if (response) {
            // Actualizar en segundo plano
            fetch(event.request).then(res => {
              caches.open(CACHE_NAME).then(cache => cache.put(event.request, res));
            }).catch(() => {});
            return response;
          }
          return fetch(event.request).then(response => {
            if (!response || response.status !== 200 || response.type !== 'basic') {
              return response;
            }
            const responseToCache = response.clone();
            caches.open(CACHE_NAME)
              .then(cache => {
                cache.put(event.request, responseToCache);
              });
            return response;
          });
        })
    );
  }
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
    })
  );
});
