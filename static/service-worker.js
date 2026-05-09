self.addEventListener("install", function (event) {
    event.waitUntil(
        caches.open("autopartes-cache").then(function (cache) {
            return cache.addAll([
                "/",
                "/login",
                "/admin"
            ]);
        })
    );
});

self.addEventListener("fetch", function (event) {
    event.respondWith(
        caches.match(event.request).then(function (response) {
            return response || fetch(event.request);
        })
    );
});