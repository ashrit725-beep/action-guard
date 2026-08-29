/* Vexen service worker — only job is to show a nudge when an agent is waiting.

   It deliberately does nothing else: no caching, no offline shell, no fetch
   interception. That keeps the app's normal behaviour completely unchanged. */

self.addEventListener("install", () => {
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(self.clients.claim());
});

self.addEventListener("push", (event) => {
  let data = {};
  try {
    data = event.data ? event.data.json() : {};
  } catch (err) {
    data = { title: "Vexen", body: "An agent needs your attention." };
  }

  const title = data.title || "Vexen";
  const options = {
    body: data.body || "An agent needs your attention.",
    tag: data.tag || "vexen",
    renotify: true,
    requireInteraction: Boolean(data.requireInteraction),
    icon: "/icons/vexen-192.png",
    badge: "/icons/vexen-badge.png",
    data: { url: data.url || "/app/approvals" },
  };

  // waitUntil keeps the worker alive until the notification is actually shown.
  event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const target = (event.notification.data && event.notification.data.url) || "/app/approvals";

  event.waitUntil(
    self.clients.matchAll({ type: "window", includeUncontrolled: true }).then((clientList) => {
      // Reuse an open tab where we can, so people do not collect duplicates.
      for (const client of clientList) {
        if ("focus" in client) {
          if (client.url === target) return client.focus();
        }
      }
      if (self.clients.openWindow) return self.clients.openWindow(target);
      return undefined;
    }),
  );
});
