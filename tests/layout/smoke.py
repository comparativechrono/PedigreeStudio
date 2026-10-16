"""Checks of Tidy inside the Studio: the button, undo and redo, partner lines
drawn over people, raised sibship lines, saving and loading, and the PNG and
SVG exports.

usage: python3 smoke.py [PAGE]"""
import json, os, sys
from playwright.sync_api import sync_playwright
HERE = os.path.dirname(os.path.abspath(__file__))
page = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.join(HERE, '..', '..', 'index.html')
OUT = os.path.join(HERE, 'out', 'smoke')
os.makedirs(OUT, exist_ok=True)
if not os.path.isdir(os.path.join(HERE, 'fixtures')):
    import fixtures
    fixtures.main()
fx = lambda n: json.load(open(os.path.join(HERE, 'fixtures', n)))
fails = []
def check(cond, msg):
    print(('ok   ' if cond else 'FAIL ') + msg)
    if not cond: fails.append(msg)
with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={'width': 1400, 'height': 900}, accept_downloads=True)
    pg = ctx.new_page()
    errors = []
    pg.on('pageerror', lambda e: errors.append(str(e)))
    pg.on('dialog', lambda d: d.accept())
    pg.goto('file://' + page); pg.wait_for_timeout(400)
    pg.evaluate("() => { try { dismissSplash(); } catch (e) {} try { localStorage.clear(); } catch (e) {} }")
    data = fx('05-three-partners__neat.json')
    pg.evaluate("(d) => { restoreSession(d); updateAllConnections(); }", data)
    before = pg.evaluate("() => Array.from(persons.values()).map(p => [p.id, p.el.style.left, p.el.style.top])")
    # Tidy, as the toolbar button runs it
    pg.evaluate("() => redistributePedigreeWithWarning()")
    pg.wait_for_timeout(200)
    after = pg.evaluate("() => Array.from(persons.values()).map(p => [p.id, p.el.style.left, p.el.style.top])")
    check(before != after, 'Tidy moved people')
    routed = pg.evaluate("() => partnerships.filter(p => p.routeEl).map(p => [p.id, p.el.getAttribute('stroke-dasharray'), p.routeEl.getAttribute('d').slice(0, 40)])")
    check(len(routed) == 1, 'one partner line is drawn over someone: %s' % routed)
    status = pg.evaluate("() => document.getElementById('statusBar').textContent")
    check('tidied' in status.lower(), 'status bar says tidied: %r' % status)
    # undo
    pg.evaluate("() => undo()"); pg.wait_for_timeout(100)
    undone = pg.evaluate("() => Array.from(persons.values()).map(p => [p.id, p.el.style.left, p.el.style.top])")
    check(undone == before, 'undo restores the drawing')
    pg.evaluate("() => redo()"); pg.wait_for_timeout(100)
    redone = pg.evaluate("() => Array.from(persons.values()).map(p => [p.id, p.el.style.left, p.el.style.top])")
    check(redone == after, 'redo brings the tidy back')
    # staggered sibship lines survive save and load
    d23 = fx('23-many-joins__neat.json')
    pg.evaluate("(d) => { restoreSession(d); updateAllConnections(); redistributePedigreeWithWarning(); }", d23)
    offs = pg.evaluate("() => childLinks.filter(c => c.branchYOffset).length")
    check(offs > 0, 'some sibship lines are raised (%d)' % offs)
    ses = pg.evaluate("() => JSON.stringify(buildSessionData())")
    pg.evaluate("(s) => { restoreSession(JSON.parse(s)); }", ses)
    offs2 = pg.evaluate("() => childLinks.filter(c => c.branchYOffset).length")
    check(offs2 == offs, 'raised sibship lines survive save and load (%d)' % offs2)
    dpaths = pg.evaluate("() => childLinks.filter(c => c.branchYOffset).map(c => c.els[0].getAttribute('d')).slice(0, 2)")
    check(all(dpaths), 'their paths are drawn')
    # routes survive save and load
    pg.evaluate("(d) => { restoreSession(d); updateAllConnections(); redistributePedigreeWithWarning(); }", data)
    ses = pg.evaluate("() => JSON.stringify(buildSessionData())")
    pg.evaluate("(s) => { restoreSession(JSON.parse(s)); }", ses)
    pg.wait_for_timeout(100)
    routed2 = pg.evaluate("() => partnerships.filter(p => p.routeEl).length")
    check(routed2 == 1, 'the drawn-over line comes back after loading')
    # dragging the person in the way off the line removes the arch
    pg.evaluate("""() => { const ps = partnerships.find(p => p.routeEl); const fromP = persons.get(ps.fromId); 
      persons.forEach(q => { if (q.id !== ps.fromId && q.id !== ps.toId && Math.abs(parseFloat(q.el.style.top) - parseFloat(fromP.el.style.top)) < 2) {
        const l = parseFloat(q.el.style.left), lo = Math.min(parseFloat(fromP.el.style.left), parseFloat(persons.get(ps.toId).el.style.left)), hi = Math.max(parseFloat(fromP.el.style.left), parseFloat(persons.get(ps.toId).el.style.left));
        if (l > lo && l < hi) { q.el.style.top = (parseFloat(q.el.style.top) + 200) + 'px'; } } });
      updateAllConnections(); }""")
    routed3 = pg.evaluate("() => partnerships.filter(p => p.routeEl).length")
    dash = pg.evaluate("() => partnerships.filter(p => p.el.getAttribute('stroke-dasharray')).length")
    check(routed3 == 0 and dash == 0, 'moving the person out of the way straightens the line')
    # exports
    pg.evaluate("(d) => { restoreSession(d); updateAllConnections(); redistributePedigreeWithWarning(); }", data)
    with pg.expect_download() as dl:
        pg.evaluate("() => saveAsSVG()")
    svgp = os.path.join(OUT, 'export.svg'); dl.value.save_as(svgp)
    svg = open(svgp).read()
    check('<path d="M ' in svg and ' Q ' in svg, 'SVG export draws the arch')
    with pg.expect_download() as dl2:
        pg.evaluate("() => saveAsImage()")
    pngp = os.path.join(OUT, 'export.png'); dl2.value.save_as(pngp)
    check(os.path.getsize(pngp) > 5000, 'PNG export written (%d bytes)' % os.path.getsize(pngp))
    # highlight follows the arch
    pg.evaluate("() => { const ps = partnerships.find(p => p.routeEl); ps.el.classList.add('highlighted'); }")
    col = pg.evaluate("() => { const ps = partnerships.find(p => p.routeEl); return getComputedStyle(ps.routeEl).stroke; }")
    check(col and col != 'rgb(26, 35, 50)', 'selected line highlights its arch too (%s)' % col)
    # empty canvas: Tidy does nothing and does not throw
    pg.evaluate("() => { clearAll && clearAll(); }")
    pg.evaluate("() => redistributePedigreeWithWarning()")
    check(not errors, 'no page errors: %s' % errors[:3])
    pg.screenshot(path=os.path.join(OUT, 'final.png'))
    b.close()
print('failures:', len(fails))
sys.exit(1 if fails else 0)
