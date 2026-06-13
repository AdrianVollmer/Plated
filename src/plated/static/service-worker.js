// Minimal service worker - required for PWA installability.
// No caching: all requests go to the network.
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', (event) => {
    // Clean up any caches left over from a previous version
    event.waitUntil(
        caches.keys().then((names) => Promise.all(names.map((n) => caches.delete(n))))
    );
    return self.clients.claim();
});
