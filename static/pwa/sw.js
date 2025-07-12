// Service Worker para Grúa Style PWA
const CACHE_NAME = 'grua-style-v1.0.0';
const STATIC_CACHE = 'grua-style-static-v1.0.0';
const DYNAMIC_CACHE = 'grua-style-dynamic-v1.0.0';

// Archivos críticos para cachear
const staticAssets = [
  '/',
  '/dashboard/',
  '/solicitar-servicio/',
  '/static/pwa/manifest.json',
  '/static/pwa/icon-192x192.png',
  '/static/pwa/icon-512x512.png',
  // Agregar aquí más archivos CSS/JS críticos cuando los tengas
];

// URLs que siempre necesitan red
const networkFirst = [
  '/admin/',
  '/registro/',
  '/login/',
  '/logout/',
  '/api/'
];

// URLs que pueden funcionar con cache
const cacheFirst = [
  '/static/',
  '/dashboard/',
  '/'
];

// Instalación del Service Worker
self.addEventListener('install', event => {
  console.log('🚀 Grúa Style SW: Instalando...');
  
  event.waitUntil(
    caches.open(STATIC_CACHE)
      .then(cache => {
        console.log('📦 Grúa Style SW: Cacheando archivos estáticos');
        return cache.addAll(staticAssets);
      })
      .then(() => {
        console.log('✅ Grúa Style SW: Instalación completa');
        return self.skipWaiting();
      })
      .catch(error => {
        console.error('❌ Grúa Style SW: Error en instalación:', error);
      })
  );
});

// Activación del Service Worker
self.addEventListener('activate', event => {
  console.log('🔄 Grúa Style SW: Activando...');
  
  event.waitUntil(
    caches.keys()
      .then(cacheNames => {
        return Promise.all(
          cacheNames.map(cacheName => {
            if (cacheName !== STATIC_CACHE && cacheName !== DYNAMIC_CACHE) {
              console.log('🗑️ Grúa Style SW: Eliminando cache obsoleto:', cacheName);
              return caches.delete(cacheName);
            }
          })
        );
      })
      .then(() => {
        console.log('✅ Grúa Style SW: Activación completa');
        return self.clients.claim();
      })
  );
});

// Interceptar peticiones de red
self.addEventListener('fetch', event => {
  const requestURL = new URL(event.request.url);
  
  // Ignorar peticiones no HTTP
  if (!event.request.url.startsWith('http')) {
    return;
  }
  
  // Estrategia Network First para URLs críticas
  if (networkFirst.some(path => requestURL.pathname.startsWith(path))) {
    event.respondWith(networkFirstStrategy(event.request));
    return;
  }
  
  // Estrategia Cache First para archivos estáticos
  if (cacheFirst.some(path => requestURL.pathname.startsWith(path))) {
    event.respondWith(cacheFirstStrategy(event.request));
    return;
  }
  
  // Estrategia Stale While Revalidate para el resto
  event.respondWith(staleWhileRevalidate(event.request));
});

// Estrategia Network First
async function networkFirstStrategy(request) {
  try {
    const networkResponse = await fetch(request);
    const cache = await caches.open(DYNAMIC_CACHE);
    cache.put(request, networkResponse.clone());
    return networkResponse;
  } catch (error) {
    console.log('🌐 Red no disponible, buscando en cache:', request.url);
    const cachedResponse = await caches.match(request);
    return cachedResponse || new Response('Offline - Grúa Style', {
      status: 200,
      headers: { 'Content-Type': 'text/html' }
    });
  }
}

// Estrategia Cache First  
async function cacheFirstStrategy(request) {
  const cachedResponse = await caches.match(request);
  if (cachedResponse) {
    return cachedResponse;
  }
  
  try {
    const networkResponse = await fetch(request);
    const cache = await caches.open(DYNAMIC_CACHE);
    cache.put(request, networkResponse.clone());
    return networkResponse;
  } catch (error) {
    return new Response('Offline - Grúa Style', {
      status: 200,
      headers: { 'Content-Type': 'text/html' }
    });
  }
}

// Estrategia Stale While Revalidate
async function staleWhileRevalidate(request) {
  const cache = await caches.open(DYNAMIC_CACHE);
  const cachedResponse = await cache.match(request);
  
  const networkPromise = fetch(request).then(response => {
    cache.put(request, response.clone());
    return response;
  }).catch(() => cachedResponse);
  
  return cachedResponse || networkPromise;
}

// Manejo de notificaciones push (para futuro)
self.addEventListener('push', event => {
  console.log('📬 Grúa Style SW: Notificación recibida');
  
  const options = {
    body: event.data ? event.data.text() : 'Nueva actualización de Grúa Style',
    icon: '/static/pwa/icon-192x192.png',
    badge: '/static/pwa/badge-72x72.png',
    vibrate: [100, 50, 100, 50, 100],
    data: {
      dateOfArrival: Date.now(),
      primaryKey: 1,
      url: '/'
    },
    actions: [
      {
        action: 'explore',
        title: 'Ver Detalles 👁️',
        icon: '/static/pwa/action-view.png'
      },
      {
        action: 'close',
        title: 'Cerrar ❌',
        icon: '/static/pwa/action-close.png'
      }
    ],
    requireInteraction: true
  };

  event.waitUntil(
    self.registration.showNotification('🚗 Grúa Style', options)
  );
});

// Manejo de clics en notificaciones
self.addEventListener('notificationclick', event => {
  console.log('🔔 Grúa Style SW: Click en notificación');
  
  event.notification.close();
  
  if (event.action === 'explore') {
    event.waitUntil(
      clients.openWindow(event.notification.data.url || '/')
    );
  } else if (event.action === 'close') {
    // Solo cerrar la notificación
  } else {
    // Click en la notificación principal
    event.waitUntil(
      clients.openWindow('/')
    );
  }
});

// Sincronización en segundo plano (para futuras funciones offline)
self.addEventListener('sync', event => {
  console.log('🔄 Grúa Style SW: Sincronización en segundo plano');
  
  if (event.tag === 'background-sync') {
    event.waitUntil(
      // Aquí puedes agregar lógica para sincronizar datos offline
      console.log('🔄 Sincronizando datos offline...')
    );
  }
});