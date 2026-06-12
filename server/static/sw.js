// Self-destruct service worker.
// A SW was caching the app shell and trapping devices on stale builds. This
// version clears all caches and unregisters itself, then reloads open pages so
// the app always loads fresh from the network from now on.
self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (e) => {
  e.waitUntil((async () => {
    try {
      const keys = await caches.keys();
      await Promise.all(keys.map((k) => caches.delete(k)));
      await self.registration.unregister();
      const clients = await self.clients.matchAll({ type: "window" });
      clients.forEach((c) => c.navigate(c.url));
    } catch (e) {}
  })());
});
