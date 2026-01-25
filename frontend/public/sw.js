/**
 * Service Worker for Phonox PWA
 * Enables offline caching and app-like experience
 */

const CACHE_NAME = 'phonox-v2'
const STATIC_ASSETS = [
  '/manifest.json',
  '/icon-192.svg',
  '/icon-512.svg'
]

// Install: Cache essential assets
self.addEventListener('install', (event) => {
  console.log('SW: Installing version', CACHE_NAME)
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(STATIC_ASSETS).catch(() => {
        // Some assets may not exist yet (like icons)
        return Promise.resolve()
      })
    })
  )
  // Don't take control immediately to prevent flickering
})

// Activate: Clean up old caches
self.addEventListener('activate', (event) => {
  console.log('SW: Activating version', CACHE_NAME)
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cacheName) => {
          if (cacheName !== CACHE_NAME) {
            console.log('SW: Deleting old cache', cacheName)
            return caches.delete(cacheName)
          }
        })
      )
    })
  )
  // Don't claim clients immediately to prevent flickering
})

// Fetch: Network first, fall back to cache
self.addEventListener('fetch', (event) => {
  // Skip non-GET requests
  if (event.request.method !== 'GET') {
    return
  }

  const url = new URL(event.request.url)
  
  // Always try network first for HTML, JS, and CSS files to prevent stale content
  if (url.pathname.endsWith('.html') || 
      url.pathname.endsWith('.js') || 
      url.pathname.endsWith('.css') || 
      url.pathname === '/' ||
      url.pathname.includes('assets/')) {
    
    event.respondWith(
      fetch(event.request)
        .then(response => {
          // Cache successful responses
          if (response.ok) {
            const responseClone = response.clone()
            caches.open(CACHE_NAME).then(cache => {
              cache.put(event.request, responseClone)
            })
          }
          return response
        })
        .catch(() => {
          // Fall back to cache if network fails
          return caches.match(event.request)
        })
    )
    return
  }

  const { request } = event

  // Network first for API calls
  if (request.url.includes('/api/')) {
    event.respondWith(
      fetch(request)
        .then((response) => {
          // Don't cache non-200 responses
          if (!response || response.status !== 200) {
            return response
          }
          
          // Clone the response before caching so we can return the original
          const responseToCache = response.clone()
          caches.open(CACHE_NAME).then((cache) => {
            cache.put(request, responseToCache)
          })
          
          return response
        })
        .catch(() => {
          // Return cached API response if available
          return caches.match(request)
        })
    )
    return
  }

  // Cache first for static assets
  event.respondWith(
    caches.match(request).then((cached) => {
      if (cached) {
        return cached
      }

      return fetch(request).then((response) => {
        if (!response || response.status !== 200 || response.type !== 'basic') {
          return response
        }

        // Clone before caching
        const responseToCache = response.clone()
        caches.open(CACHE_NAME).then((cache) => {
          cache.put(request, responseToCache)
        })
        
        return response
      })
    })
  )
})
