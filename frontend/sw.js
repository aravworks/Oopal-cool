// MindEase — Service Worker
// Caches the shell for offline access.
// API calls (Supabase, Gemini) still require network.

const CACHE_NAME = "mindease-v1";
const SHELL_ASSETS = [
  "/",
  "/index.html",
  "https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=Inter:wght@300;400;500;600&family=JetBrains+Mono:wght@400;500&display=swap",
];

// Install — cache shell
self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(SHELL_ASSETS))
  );
  self.skipWaiting();
});

// Activate — clean old caches
self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

// Fetch — network first, fall back to cache for shell assets
self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);

  // Always go network for API calls
  if (
    url.hostname.includes("supabase.co") ||
    url.hostname.includes("googleapis.com") ||
    url.hostname.includes("generativelanguage") ||
    url.pathname.startsWith("/api/")
  ) {
    return; // let the browser handle it
  }

  // Shell assets: network first, cache fallback
  event.respondWith(
    fetch(event.request)
      .then((resp) => {
        const clone = resp.clone();
        caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone));
        return resp;
      })
      .catch(() => caches.match(event.request))
  );
});
