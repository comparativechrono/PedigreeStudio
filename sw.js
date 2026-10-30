// Pedigree Studio's service worker, for the copy on its website (pedigreestudio.xyz).
//
// Once the Studio has been opened from the website, the browser keeps a copy of it here, so that
// it opens again without a connection and can be installed like an app. Each time the Studio is
// opened, a newer copy is fetched if the network gives one within a few seconds; otherwise the
// kept copy opens, and a newer one that arrives later is kept for next time.
//
// The worker handles only the Studio's own files, and only fetches them: nothing drawn in the
// Studio ever reaches it. The page itself (index.html) is still one file that works on its own,
// opened from a disk or a USB stick; it uses this worker only when it is opened from the website.
//
// Change CACHE whenever the icons or the manifest change, so that browsers fetch them again.
const CACHE = 'pedigree-studio-1';
const PAGE = new URL('./', self.location).href;
const FILES = ['./', 'manifest.webmanifest', 'icons/icon-192.png', 'icons/icon-512.png',
  'icons/icon-maskable-512.png', 'apple-touch-icon.png'].map(f => new URL(f, self.location).href);
const WAIT = 3000; // how long a slow network gets before the kept copy opens (ms)

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(FILES)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', e => {
  e.waitUntil(caches.keys()
    .then(keys => Promise.all(keys.filter(k => k.startsWith('pedigree-studio-') && k !== CACHE).map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
});

self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  url.search = ''; url.hash = '';
  if (req.mode === 'navigate') {
    if (url.href === PAGE || url.href === PAGE + 'index.html') e.respondWith(openPage(e));
    return;
  }
  if (FILES.includes(url.href)) e.respondWith(caches.match(url.href).then(r => r || fetch(req)));
});

// The page: the network's copy if it comes in time (and it replaces the kept one), else the kept copy
function openPage(e) {
  let stored;
  e.waitUntil(new Promise(r => { stored = r; })); // so that a copy arriving late is still kept
  const fresh = fetch(e.request.url, { cache: 'no-cache', credentials: 'same-origin' }).then(res => {
    if (!res.ok) throw new Error('the site answered ' + res.status);
    const copy = res.clone(); // now, before the page starts to read res
    stored(caches.open(CACHE).then(c => c.put(PAGE, copy)).catch(() => {}));
    return res;
  });
  fresh.catch(() => stored());
  const kept = caches.match(PAGE);
  return new Promise(resolve => {
    let done = false;
    const answer = r => { if (!done && r) { done = true; resolve(r); } };
    const timer = setTimeout(() => kept.then(answer), WAIT);
    fresh.then(res => { clearTimeout(timer); answer(res); })
      .catch(() => { clearTimeout(timer); kept.then(r => answer(r || Response.error())); });
  });
}
