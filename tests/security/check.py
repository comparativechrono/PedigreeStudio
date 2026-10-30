"""Checks that a pedigree file cannot add to the Studio's page, run code in it or make the browser
fetch anything.

usage: python3 check.py [PAGE]
  PAGE  the Studio page to check (default: the index.html two folders up)

The check writes a drawing in which every field holds something hostile: markup inside a symbol, a
colour that is a web address, quotes that would end an attribute, numbers that are text. The Studio
opens it as a file and again as the drawing it kept in the browser. It shows the key and exports the
drawing as SVG, PNG and a file. The browser is kept offline: a request for anything but the page itself
fails the check. Everything is checked twice: on the page as it is, and on a copy without its Content
Security Policy, so that the Studio's own defences are tested, not only the browser's.

Needs Python 3 with Playwright (pip install playwright; playwright install chromium). Exits with status
1 if any check fails."""
import json, os, sys, tempfile
import xml.etree.ElementTree as ET
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
page_path = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.join(HERE, '..', '..', 'index.html')
fails = []


def check(cond, msg):
    print(('ok   ' if cond else 'FAIL ') + msg)
    if not cond:
        fails.append(msg)


RAN = "document.title='RAN'"
TAG = '<img src="https://example.invalid/a.png" onerror="%s">' % RAN
QUOTE = '"><img src="https://example.invalid/b.png" onerror="%s"><x a="' % RAN
URL = 'url(https://example.invalid/c.png)'


def person(i, **kw):
    p = {'id': 'person-%d' % i, 'shape': 'female' if i % 2 else 'male', 'x': 100 + 110 * i, 'y': 200, 'text': '',
         'deceased': False, 'proband': False, 'fillMode': 'none', 'fillColor': '#c0392b', 'quarters': [None] * 4,
         'halves': [None, None], 'centerText': ''}
    p.update(kw)
    return p


HOSTILE = {
    'version': 5, 'personIdCounter': QUOTE, 'labelIdCounter': 1, 'lineIdCounter': 1,
    'persons': [
        person(1, centerText=TAG, fillMode='solid', fillColor=QUOTE, text=TAG, customLabel=TAG),
        person(2, fillMode='half', halves=[URL, QUOTE], miscarriageSex=TAG),
        person(3, fillMode='quartered', quarters=[URL, QUOTE, TAG, '#2980b9']),
        person(4, id='person-4' + QUOTE, fillMode='shading', shadingPattern=QUOTE, shadingCoverage=TAG),
        person(5, fillMode='solid', fillColor=URL, x=QUOTE, y=TAG, shape=TAG),
        person(6, fillMode='shading', shadingPattern='dots', shadingCoverage='half-left', deceased=TAG),
    ],
    'labels': [{'id': 'label-1', 'x': 100, 'y': 420, 'text': TAG, 'size': QUOTE, 'bordered': True}],
    'partnerships': [{'id': 'pship-1', 'fromId': 'person-1', 'toId': 'person-2', 'type': TAG}],
    'childLinks': [{'id': 'cl-1', 'partnershipId': 'pship-1', 'childId': 'person-3', 'branchYOffset': QUOTE,
                    'dashed': TAG}],
    'twinLinks': [{'id': TAG, 'child1Id': QUOTE, 'child2Id': 'person-3', 'type': TAG}],
    'legendLabels': {QUOTE: TAG, '#c0392b': TAG, URL: TAG, '__proto__': {'polluted': TAG}},
    'legendVisible': True, 'legendX': QUOTE, 'legendY': TAG, 'legendFit': TAG, 'legendWidth': QUOTE,
    'zoom': QUOTE, 'panX': QUOTE, 'panY': TAG, 'numberingMode': TAG,
    'partnerGapMultiplier': QUOTE, 'childHeightMultiplier': TAG,
    'drawStrokes': [{'points': [{'x': QUOTE, 'y': 1}, {'x': 10, 'y': 10}, {'x': 20, 'y': 30}], 'color': URL,
                     'width': QUOTE},
                    {'points': [{'x': 30, 'y': 30}, {'x': 60, 'y': 60}], 'color': QUOTE, 'width': 3},
                    {'points': TAG, 'color': '#2980b9', 'width': 3}],
}

# what is on the page once the drawing is open
STATE = """() => {
  const attrs = [];
  document.querySelectorAll('#canvas *, #legend-box *').forEach(el => {
    for (const a of el.attributes) attrs.push([a.name, a.value]);
  });
  const shape1 = document.querySelector('#person-1 .person-shape text');
  return {
    title: document.title,
    imgs: document.querySelectorAll('img').length,
    persons: persons.size,
    handlers: attrs.filter(([n]) => n.startsWith('on')).length,
    urls: attrs.filter(([n, v]) => /url\\(\\s*['"]?(?!#)/i.test(v)).map(([n, v]) => n + '=' + v),
    swatches: Array.from(document.querySelectorAll('.legend-swatch')).map(s => s.style.background),
    centre: shape1 ? shape1.textContent : null,
    text1: (document.querySelector('#person-1 .person-text') || {}).textContent,
    proto: Object.prototype.polluted === undefined,
  };
}"""

SVG_TAGS = {'svg', 'rect', 'path', 'line', 'circle', 'text', 'g', 'defs', 'pattern', 'clipPath'}


def run(path, label):
    print('\n== %s' % label)
    url = 'file://' + path
    tmp = tempfile.mkdtemp()
    hostile = os.path.join(tmp, 'hostile.json')
    json.dump(HOSTILE, open(hostile, 'w'))
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={'width': 1400, 'height': 900}, accept_downloads=True)
        asked = []

        def offline(route):
            if not route.request.url.startswith('file:'):
                asked.append(route.request.url)
                route.abort()
            else:
                route.continue_()
        ctx.route('**/*', offline)
        pg = ctx.new_page()
        errors = []
        pg.on('pageerror', lambda e: errors.append(str(e)))
        pg.on('dialog', lambda d: d.accept())
        pg.goto(url)
        pg.wait_for_timeout(300)
        pg.evaluate("() => { try { localStorage.clear(); } catch (e) {} }")
        pg.reload()
        pg.wait_for_timeout(300)

        def look(how):
            s = pg.evaluate(STATE)
            check(s['title'] != 'RAN', '%s: nothing in the file ran' % how)
            check(s['imgs'] == 0 and s['handlers'] == 0, '%s: the file added no elements or handlers (%d img, %d on…)'
                  % (how, s['imgs'], s['handlers']))
            check(not s['urls'], '%s: no colour or style points to a file: %s' % (how, s['urls'][:2]))
            check(s['persons'] == 6, '%s: every person was drawn (%d of 6)' % (how, s['persons']))
            check(s['centre'] == TAG[:8], '%s: text inside a symbol is shown as text (%r)' % (how, s['centre']))
            check(s['text1'] == TAG, '%s: text under a symbol is shown as written' % how)
            check(len(s['swatches']) >= 3 and all('url' not in b for b in s['swatches']),
                  '%s: the key shows only colours (%d entries)' % (how, len(s['swatches'])))
            check(s['proto'], '%s: the key\'s entries cannot change objects in the page' % how)

        def download(call):
            """the file an export function downloads, or None if it failed"""
            try:
                with pg.expect_download(timeout=5000) as dl:
                    pg.evaluate('() => %s()' % call)
                return dl.value.path()
            except Exception as e:
                print('     (%s: %s)' % (call, str(e).splitlines()[0]))
                return None

        pg.set_input_files('#importFile', hostile)
        pg.wait_for_timeout(500)
        look('opened as a file')

        svg_path = download('saveAsSVG')
        check(svg_path is not None, 'the drawing exports as SVG')
        root = None
        if svg_path:
            try:
                root = ET.fromstring(open(svg_path, encoding='utf-8').read())
            except ET.ParseError as e:
                print('     (%s)' % e)
            check(root is not None, 'the SVG export is well-formed XML')
        if root is not None:
            tags = {el.tag.split('}')[-1] for el in root.iter()}
            attrs = [(k.split('}')[-1], v) for el in root.iter() for k, v in el.attrib.items()]
            check(tags <= SVG_TAGS, 'the SVG export holds only drawing elements: %s' % sorted(tags - SVG_TAGS))
            check(not [k for k, v in attrs if k.startswith('on') or k == 'href'],
                  'the SVG export has no event handlers or links')
            bad = [v for k, v in attrs if 'url(' in v and not v.startswith('url(#')]
            check(not bad, 'no colour in the SVG export points to a file: %s' % bad[:2])
            check(any((el.text or '') == TAG for el in root.iter()), 'the SVG export shows the text as written')

        png_path = download('saveAsImage')
        check(png_path is not None and os.path.getsize(png_path) > 1000, 'the drawing exports as PNG')

        json_path = download('exportJSON')
        check(json_path is not None, 'the drawing can be saved again')
        if json_path:
            saved = json.load(open(json_path))
            one = next((q for q in saved['persons'] if q['id'] == 'person-1'), {})
            check(one.get('fillColor') != QUOTE and isinstance(saved.get('legendX'), (int, float)),
                  'a drawing saved again keeps only what a drawing can hold')

        # the same drawing, kept in the browser and restored when the page opens
        pg.evaluate("(d) => localStorage.setItem('pedigree-studio-session', d)", json.dumps(HOSTILE))
        pg.reload()
        pg.wait_for_timeout(500)
        look('restored from the browser')

        check(not asked, 'the browser was asked for nothing but the page: %s' % asked[:3])
        check(not errors, 'no errors on the page: %s' % errors[:3])
        browser.close()


run(page_path, 'the page as it is')
# the same page without its Content Security Policy: the Studio's own checks must hold by themselves
html = open(page_path, encoding='utf-8').read()
start = html.find('<meta http-equiv="Content-Security-Policy"')
check(start >= 0, 'the page has a Content Security Policy')
if start >= 0:
    bare = os.path.join(os.path.dirname(page_path), '.no-csp-check.html')
    with open(bare, 'w', encoding='utf-8') as f:
        f.write(html[:start] + html[html.index('>', start) + 1:])
    try:
        run(bare, 'the page without its Content Security Policy')
    finally:
        os.remove(bare)

print('\n%d failed' % len(fails) if fails else '\nall passed')
sys.exit(1 if fails else 0)
