"""Checks of Pedigree Studio as its website serves it: that it can be installed, that once opened
it opens again without a connection, that a newer copy of the page replaces the kept one (even
over a slow network), that nothing goes to the network while someone draws, and that a copy
opened from a file, or inside another page, does none of this.

usage: python3 check.py [SITE]
  SITE  the folder the website is served from (default: the repository, two folders up)

The site is served from http://127.0.0.1, which browsers treat as secure, as they do https.
Needs Python 3 with Playwright (pip install playwright; playwright install chromium).
Exits with status 1 if any check fails."""
import http.server, os, shutil, socketserver, sys, tempfile, threading, time
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.join(HERE, '..', '..')
FILES = ['index.html', 'sw.js', 'manifest.webmanifest', 'icons/icon-192.png', 'icons/icon-512.png',
         'icons/icon-maskable-512.png', 'apple-touch-icon.png']
fails = []


def check(cond, msg):
    print(('ok   ' if cond else 'FAIL ') + msg)
    if not cond:
        fails.append(msg)


class Site:
    """The website, in memory, so that the page can be changed or slowed down between visits."""
    def __init__(self):
        self.files = {'/' + f: open(os.path.join(SITE, f), 'rb').read() for f in FILES}
        self.files['/'] = self.files['/index.html']
        self.files['/frame.html'] = b'<!DOCTYPE html><title>Another page</title><iframe src="index.html" width="900" height="600"></iframe>'
        self.delay = 0
        self.log = []
        self.server = None
        self.port = 0

    def set_page(self, text):
        self.files['/'] = self.files['/index.html'] = text.encode('utf-8')

    def start(self):
        site = self

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                path = self.path.split('?')[0]
                site.log.append(path)
                if path in ('/', '/index.html') and site.delay:
                    time.sleep(site.delay)
                body = site.files.get(path)
                if body is None:
                    self.send_response(404)
                    self.end_headers()
                    return
                kind = {'.html': 'text/html; charset=utf-8', '.js': 'text/javascript', '.png': 'image/png',
                        '.webmanifest': 'application/manifest+json'}
                self.send_response(200)
                self.send_header('Content-Type', next((v for k, v in kind.items() if path.endswith(k)), 'text/html; charset=utf-8'))
                self.send_header('Cache-Control', 'max-age=600')  # as GitHub Pages sends
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *a):
                pass

        class Server(socketserver.ThreadingTCPServer):
            allow_reuse_address = True
            daemon_threads = True
        self.server = Server(('127.0.0.1', self.port), Handler)
        self.port = self.server.server_address[1]
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def stop(self):
        self.server.shutdown()
        self.server.server_close()


site = Site()
site.start()
base = 'http://127.0.0.1:%d/' % site.port
page_text = site.files['/index.html'].decode('utf-8')

with sync_playwright() as p:
    browser = p.chromium.launch()
    ctx = browser.new_context(viewport={'width': 1280, 'height': 800})
    pg = ctx.new_page()
    errors, blocked = [], []
    pg.on('pageerror', lambda e: errors.append(str(e)))
    pg.on('console', lambda m: blocked.append(m.text) if 'Content Security Policy' in m.text else None)
    ev = pg.evaluate

    # first visit, with a connection
    pg.goto(base)
    ready = ev("() => navigator.serviceWorker.ready.then(r => !!r.active)")
    check(ready, 'opened from the website, the page starts its service worker')
    pg.reload()  # from now on the worker answers for the page
    pg.wait_for_timeout(300)
    check(ev("() => !!navigator.serviceWorker.controller"), '...which then looks after the page')
    check(ev("() => !!document.querySelector('link[rel=manifest]')"), 'the page names its manifest')
    kept = ev("""() => caches.keys().then(ks => Promise.all(ks.map(k => caches.open(k).then(c => c.keys()))))
                       .then(all => all.flat().map(r => new URL(r.url).pathname).sort())""")
    want = sorted(['/'] + ['/' + f for f in FILES if f not in ('index.html', 'sw.js')])
    check(kept == want, 'the worker keeps the page, the manifest and the icons, and nothing else: %s' % kept)
    cdp = ctx.new_cdp_session(pg)
    man = cdp.send('Page.getAppManifest')
    check(not man.get('errors'), 'the manifest reads without errors: %s' % man.get('errors'))
    inst = cdp.send('Page.getInstallabilityErrors')['installabilityErrors']
    check(inst == [], 'the browser can install the Studio: %s' % inst)

    # drawing, exporting and saving send nothing (once the browser has finished its own check for a newer sw.js)
    n = -1
    while n != len(site.log):
        n = len(site.log)
        pg.wait_for_timeout(2000)
    pg.click('[data-add="male"]')
    pg.click('[data-qa="partner"]')
    pg.click('[data-qa="son"]')
    pg.click('#tidyBtn')
    ev("() => { HTMLAnchorElement.prototype.click = function () {}; saveAsSVG(); saveAsImage(); exportJSON(); }")
    pg.wait_for_timeout(1500)  # the drawing is saved in the browser by now
    check(site.log[n:] == [], 'drawing, Tidy, exports and saving ask the site for nothing: %s' % site.log[n:])

    # no connection at all
    site.stop()
    res = pg.reload()
    pg.wait_for_timeout(500)
    check(res is not None and res.ok and pg.title() == 'Pedigree Studio', 'with the site gone, the page still opens')
    check(ev("() => persons.size") == 3, '...with the drawing as it was left')
    pg.click('[data-add="female"]')
    check(ev("() => persons.size") == 4, '...and drawing goes on as before')

    # a newer copy of the page replaces the kept one
    site.set_page(page_text.replace('<title>Pedigree Studio</title>', '<title>Pedigree Studio 2</title>', 1))
    site.start()
    pg.reload()
    check(pg.title() == 'Pedigree Studio 2', 'once the site is back, a newer page opens at once')
    site.stop()
    pg.reload()
    check(pg.title() == 'Pedigree Studio 2', '...and it is the one kept for next time')

    # a slow network: the kept copy opens after a few seconds; the newer copy is kept when it arrives
    site.set_page(page_text.replace('<title>Pedigree Studio</title>', '<title>Pedigree Studio 3</title>', 1))
    site.delay = 6
    site.start()
    t0 = time.time()
    pg.reload()
    took = time.time() - t0
    check(pg.title() == 'Pedigree Studio 2' and took < 5, 'over a slow network the kept copy opens after a few seconds (%.1f s)' % took)
    pg.wait_for_timeout(5000)
    site.delay = 0
    site.stop()
    pg.reload()
    check(pg.title() == 'Pedigree Studio 3', '...and the newer copy, arriving late, is kept for next time')
    check(errors == [], 'no page errors: %s' % errors)
    check(blocked == [], "nothing is stopped by the page's Content Security Policy: %s" % blocked[:3])
    ctx.close()

    # inside another page, and opened from a file: no manifest and no worker
    site.set_page(page_text)
    site.start()
    ctx = browser.new_context()
    pg = ctx.new_page()
    pg.goto(base + 'frame.html')
    pg.wait_for_timeout(1500)
    fr = pg.frames[1]
    check(fr.evaluate("() => typeof restoreSession === 'function' && !document.querySelector('link[rel=manifest]')"),
          'inside another page, the Studio works but offers no install')
    check(pg.evaluate("() => navigator.serviceWorker.getRegistrations().then(r => r.length)") == 0, '...and starts no worker')
    ctx.close()
    ctx = browser.new_context()
    pg = ctx.new_page()
    errors = []
    pg.on('pageerror', lambda e: errors.append(str(e)))
    log = []
    pg.on('request', lambda r: log.append(r.url) if not r.url.startswith(('file:', 'data:', 'blob:')) else None)
    pg.goto('file://' + os.path.join(SITE, 'index.html'))
    pg.wait_for_timeout(1000)
    check(pg.evaluate("() => !document.querySelector('link[rel=manifest]')") and log == [] and errors == [],
          'opened from a file, the page offers no install and makes no request: %s %s' % (log, errors))
    ctx.close()
    site.stop()
    browser.close()

print('failures: %d' % len(fails))
sys.exit(1 if fails else 0)
