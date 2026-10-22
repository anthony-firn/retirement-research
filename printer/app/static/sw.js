/* Only public, explicitly listed shell/library assets are stored. API calls always go to the network. */
importScripts("/static/offline-assets.js");
const CACHE = "retirement-public-" + self.RETIREMENT_OFFLINE.version;
const ASSETS = new Set(self.RETIREMENT_OFFLINE.urls);
self.addEventListener("install", event => event.waitUntil(caches.open(CACHE).then(cache => cache.addAll([...ASSETS]))));
self.addEventListener("activate", event => event.waitUntil((async () => {
  for (const name of await caches.keys()) if (name.startsWith("retirement-public-") && name !== CACHE) await caches.delete(name);
  await self.clients.claim();
})()));
self.addEventListener("fetch", event => {
  const url = new URL(event.request.url);
  if (event.request.method !== "GET" || url.origin !== self.location.origin || url.search || !ASSETS.has(url.pathname)) return;
  event.respondWith((async () => {
    const cache = await caches.open(CACHE);
    try {
      const response = await fetch(event.request);
      if (response.ok) await cache.put(url.pathname, response.clone());
      return response;
    } catch {
      return await cache.match(url.pathname) || new Response("Connect to download this public resource.", { status: 503 });
    }
  })());
});
