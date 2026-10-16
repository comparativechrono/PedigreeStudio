"""Run Tidy on every test pedigree, measure the result and take a picture.

usage: python3 run.py [PAGE] [--out NAME] [--only a,b,c]
  PAGE   the Studio page to test (default: the index.html two folders up)
  --out  folder name under out/ for results.json and pictures (default: the
         page's file name)
  --only run just the fixtures whose names contain one of these

Needs Python 3 with Playwright (pip install playwright; playwright install
chromium). Writes the fixtures first if fixtures/ is missing."""
import json, os, sys
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
args = sys.argv[1:]
def opt(name, default):
    if name in args:
        i = args.index(name); v = args[i + 1]; del args[i:i + 2]; return v
    return default
tag = opt('--out', None)
only = opt('--only', '')
page = os.path.abspath(args[0]) if args else os.path.join(HERE, '..', '..', 'index.html')
tag = tag or os.path.splitext(os.path.basename(page))[0]
if not os.path.isdir(os.path.join(HERE, 'fixtures')):
    import fixtures
    fixtures.main()
names = json.load(open(os.path.join(HERE, 'fixtures', 'index.json')))
if only:
    names = [n for n in names if any(f in n for f in only.split(','))]
out = os.path.join(HERE, 'out', tag)
os.makedirs(out, exist_ok=True)
metrics_js = open(os.path.join(HERE, 'metrics.js')).read()

RUN = """(data) => {
  restoreSession(data);
  updateAllConnections(); updateTextWrapping(); updateNumbering();
  const initial = new Map();
  persons.forEach((p, id) => initial.set(id, { x: parseFloat(p.el.style.left), y: parseFloat(p.el.style.top) }));
  individualMoveMode = false;
  const t0 = performance.now();
  let err = null;
  try {
    runManagedPedigreeLayout({ seedIds: Array.from(persons.keys()), reason: 'manualRedistribute', fromButton: true, fresh: true });
  } catch (e) { err = String(e && e.stack || e); }
  const ms = performance.now() - t0;
  updateAllConnections(); updateTextWrapping();
  const m = LayoutMetrics(initial);
  m.ms = Math.round(ms);
  if (err) m.error = err;
  return m;
}"""

results = {}
with sync_playwright() as p:
    browser = p.chromium.launch()
    pg = browser.new_context(viewport={'width': 1500, 'height': 950}).new_page()
    errors = []
    pg.on('pageerror', lambda e: errors.append(str(e)))
    pg.on('dialog', lambda d: d.accept())
    pg.goto('file://' + page)
    pg.wait_for_timeout(400)
    pg.add_script_tag(content=metrics_js)
    pg.evaluate("() => { try { dismissSplash(); } catch (e) {} try { localStorage.clear(); } catch (e) {} }")
    for n in names:
        data = json.load(open(os.path.join(HERE, 'fixtures', n)))
        errors.clear()
        m = pg.evaluate(RUN, data)
        if errors:
            m['pageErrors'] = errors[:3]
        pg.evaluate("() => { fitToView(); }")
        pg.wait_for_timeout(100)
        pg.locator('#canvasArea').screenshot(path=os.path.join(out, n.replace('.json', '.png')))
        results[n] = m
        flag = '  ERROR' if m.get('error') or m.get('pageErrors') else ''
        print('%-42s score %6d  %5d ms%s' % (n, m['score'], m['ms'], flag))
    browser.close()
rp = os.path.join(out, 'results.json')
prev = json.load(open(rp)) if only and os.path.exists(rp) else {}
prev.update(results)
json.dump(prev, open(rp, 'w'), indent=1)
print('total score', sum(r['score'] for r in results.values()), 'over', len(results), 'pedigrees; results in', rp)
