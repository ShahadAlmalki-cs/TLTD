// يخزّن ملفات الواجهة فقط (لا بيانات شخصية)، ويستقبل الإشعارات.
var C = 'tltd-v4';
self.addEventListener('install', function (e) { e.waitUntil(caches.open(C).then(function (c) { return c.addAll(['/static/style.css', '/static/app.js']); })); });
self.addEventListener('fetch', function (e) {
  var u = new URL(e.request.url);
  if (e.request.method === 'GET' && u.pathname.indexOf('/static/') === 0)
    e.respondWith(fetch(e.request).catch(function () { return caches.match(e.request); }));
});
self.addEventListener('push', function (e) {
  var d = {}; try { d = e.data.json(); } catch (x) {}
  e.waitUntil(self.registration.showNotification(d.title || 'TLTD', {body: d.body || '', icon: '/static/icon-192.png', badge: '/static/icon-192.png', lang: 'ar', dir: 'rtl', data: {url: d.url || '/'}}));
});
self.addEventListener('notificationclick', function (e) {
  e.notification.close();
  e.waitUntil(clients.matchAll({type: 'window'}).then(function (cs) {
    for (var i = 0; i < cs.length; i++) if ('focus' in cs[i]) return cs[i].focus();
    return clients.openWindow(e.notification.data.url || '/');
  }));
});
