/**
 * Service Worker for Phonox PWA - DISABLED
 * Auto-refresh issues on mobile - disabled pending further optimization
 */

// Service Worker intentionally disabled to prevent mobile caching issues
// This ensures fresh content loads from server on each visit

/**
 * Service Worker for Phonox PWA - COMPLETELY DISABLED
 * All caching functionality disabled to prevent mobile issues
 * All requests go directly through to network
 */

// Unregister all service workers and clear all caches
self.addEventListener('install', (event) => {
  console.log('SW: Install - Skipping installation')
  self.skipWaiting()
})

self.addEventListener('activate', (event) => {
  console.log('SW: Activate - Clearing all caches')
  event.waitUntil(
    Promise.all([
      // Clear all caches
      caches.keys().then((cacheNames) => {
        return Promise.all(
          cacheNames.map((cacheName) => {
            console.log('SW: Deleting cache:', cacheName)
            return caches.delete(cacheName)
          })
        )
      }),
      // Take control of all pages (no messaging to avoid channel closing error)
      self.clients.matchAll().then((clients) => {
        console.log('SW: Matched', clients.length, 'clients')
        // Don't send messages to clients - causes "message channel closed" error
      })
    ])
  )
  self.clients.claim()
})

self.addEventListener('fetch', (event) => {
  // Pass through all requests directly to network
  // NO caching whatsoever
})
