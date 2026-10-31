"""Checks that a pedigree file cannot add to the Studio's page, run code in it or make the browser
fetch anything.

usage: python3 check.py [PAGE] [--key NAME] [--no-policy]
  PAGE         the Studio page to check (default: the index.html two folders up); a copy of the Studio
               elsewhere, such as the workbench's or the practical's, can be checked too
  --key NAME   the name under which the page keeps its drawing in the browser (default: the one the
               page's own code names, or else pedigree-studio-session)
  --no-policy  the page is not expected to have a Content Security Policy (a copy that has none)

The check writes a drawing in which every field holds something hostile: markup inside a symbol, a
colour that is a web address, quotes that would end an attribute, numbers that are text. The Studio
opens it as a file and again as the drawing it kept in the browser. It shows the key and exports the
drawing as SVG, PNG and a file. The browser is kept offline: a request for anything but the page itself
fails the check. Everything is checked twice: on the page as it is, and on a copy without its Content
Security Policy, so that the Studio's own defences are tested, not only the browser's.

Needs Python 3 with Playwright (pip install playwright; playwright install chromium). Exits with status
1 if any check fails."""
import argparse, json, os, re, sys, tempfile
import xml.etree.ElementTree as ET
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
ap = argparse.ArgumentParser()
ap.add_argument('page', nargs='?', default=os.path.join(HERE, '..', '..', 'index.html'))
ap.add_argument('--key')
ap.add_argument('--no-policy', action='store_true')
args = ap.parse_args()
page_path = os.path.abspath(args.page)
named = re.search(r"localStorage\.getItem\('([^']+)'\)", open(page_path, encoding='utf-8').read())
key = args.key or (named.group(1) if named else 'pedigree-studio-session')
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
        person(2, fillMode='half', halves=[URL, 'constructor'], miscarriageSex=TAG,
               text='a note with characters XML forbids: \x01 \x0b \ufffe'),
        person(3, fillMode='quartered', quarters=[URL, QUOTE, TAG, '#2980b9']),
        person(4, id='person-4' + QUOTE, fillMode='shading', shadingPattern=QUOTE, shadingCoverage=TAG),
        person(5, fillMode='solid', fillColor=URL, x=QUOTE, y=TAG, shape=TAG),
        person(6, fillMode='shading', shadingPattern='dots', shadingCoverage='half-left', deceased=TAG),
        person(7, id='person-99999999999999999999',  # (new people must still get ids of their own)
               fillMode='thirds', thirds=[URL, QUOTE, '#2980b9', TAG], shape='constructor'),
        # ids the page itself uses, an id too long to be one, and the same id twice: all left out
        person(8, id='statusBar'), person(9, id='legend-box'), person(10, id='importFile'),
        person(11, id='shpat-1'), person(12, id='p' * 300), person(13, id='person-1'),
    ],
    'labels': [{'id': 'label-1', 'x': 100, 'y': 420, 'text': TAG, 'size': QUOTE, 'bordered': True},
               {'id': 'label-2', 'text': 'a label with no place'}],
    'partnerships': [{'id': 'pship-1', 'fromId': 'person-1', 'toId': 'person-2', 'type': TAG},
                     {'id': 'constructor', 'fromId': 'person-5', 'toId': 'person-6', 'type': 'normal'},
                     {'id': 'pship-9', 'fromId': 'statusBar', 'toId': 'person-6'}],
    'childLinks': [{'id': 'cl-1', 'partnershipId': 'pship-1', 'childId': 'person-3', 'branchYOffset': QUOTE,
                    'dashed': TAG},
                   {'id': 'cl-2', 'partnershipId': 'constructor', 'childId': 'person-7'},
                   {'id': 'cl-3', 'partnershipId': 'constructor', 'childId': 'person-99999999999999999999'}],
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
    ownParts: !!document.getElementById('statusBar') && !document.getElementById('statusBar').closest('#canvas')
      && !!document.getElementById('importFile') && !document.getElementById('importFile').closest('#canvas')
      && (document.getElementById('legend-box') || {}).className.startsWith('legend-box'),
    keyText: Array.from(document.querySelectorAll('.legend-input')).map(f => f.value).join(' '),
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
            check(s['persons'] == 7, '%s: every person with an id of their own was drawn (%d of 7)' % (how, s['persons']))
            check(s['ownParts'], '%s: no one took an id the page uses, and its status bar, file input and key still work' % how)
            check('function' not in s['keyText'], '%s: the key shows nothing of the page\'s own code' % how)
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
        try:
            pg.evaluate('() => alignConnectedPersons()')
            lined_up = True
        except Exception as e:
            lined_up = False
            print('     (%s)' % str(e).splitlines()[0])
        check(lined_up, 'people line up again after a drag although a couple is called "constructor"')
        try:
            new = pg.evaluate("() => { const n = persons.size, a = addPerson(), b = addPerson(); return [a.id, b.id, persons.size - n]; }")
        except Exception as e:
            new = [None, None, 0]
            print('     (%s)' % str(e).splitlines()[0])
        check(new[0] != new[1] and new[2] == 2, 'people added afterwards get ids of their own (%s, %s)' % (new[0], new[1]))

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
            check('NaN' not in root.get('viewBox', ''), 'the SVG export has a size (%s)' % root.get('viewBox'))

        png_path = download('saveAsImage')
        check(png_path is not None and os.path.getsize(png_path) > 1000, 'the drawing exports as PNG')

        json_path = download('exportJSON')
        check(json_path is not None, 'the drawing can be saved again')
        if json_path:
            saved = json.load(open(json_path))
            one = next((q for q in saved['persons'] if q['id'] == 'person-1'), {})
            check(one.get('fillColor') != QUOTE and isinstance(saved.get('legendX'), (int, float)),
                  'a drawing saved again keeps only what a drawing can hold')

        # a file that is not a drawing, and one too big to draw, leave the drawing and Undo as they are
        for name, data in (('package.json', {'name': 'x', 'version': '1.0.0', 'dependencies': {}}),
                           ('many.json', {'version': 5, 'persons': [person(i) for i in range(1, 1002)]})):
            path = os.path.join(tmp, name)
            json.dump(data, open(path, 'w'))
            before = pg.evaluate('() => [persons.size, undoStack.length, redoStack.length]')
            pg.set_input_files('#importFile', path)
            pg.wait_for_timeout(400)
            after = pg.evaluate('() => [persons.size, undoStack.length, redoStack.length]')
            check(after == before, '%s is turned away, and the drawing and Undo stay as they were' % name)

        # a family far bigger than any drawn by hand opens in seconds, not minutes: 600 people without a place,
        # and the most tangled family the Studio draws (1,000 people, everyone related, 1,498 lines)
        many = {'version': 5, 'persons': [person(i, x=None, y=None) for i in range(1, 601)]}
        ms = pg.evaluate('(d) => { const t = performance.now(); restoreSession(d); return performance.now() - t; }', many)
        check(ms < 5000, 'a drawing of 600 people without places opens in %.1f s' % (ms / 1000))
        tangled = {'version': 5, 'persons': [person(i, x=(i % 40) * 110, y=(i // 40) * 160, text='b. 1950')
                                             for i in range(1, 1001)],
                   'partnerships': [{'id': 'pship-%d' % k, 'fromId': 'person-%d' % (2 * k - 1), 'toId': 'person-%d' % (2 * k)}
                                    for k in range(1, 501)],
                   'childLinks': [{'id': 'child-%d' % c, 'partnershipId': 'pship-%d' % (c % 500 + 1),
                                   'childId': 'person-%d' % (c % 1000 + 1)} for c in range(998)]}
        ms = pg.evaluate('(d) => { const t = performance.now(); restoreSession(d); return performance.now() - t; }', tangled)
        check(ms < 20000, 'a family of 1,000 people, all related, opens in %.1f s' % (ms / 1000))
        pg.wait_for_timeout(1500)  # (so that the Studio's own saving of it is done before the next step)

        # the same drawing, kept in the browser and restored when the page opens
        pg.evaluate("([k, d]) => localStorage.setItem(k, d)", [key, json.dumps(HOSTILE)])
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
if not args.no_policy:
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
