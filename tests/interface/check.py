"""Checks of the Studio's interface: the toolbar and its menus, the selection
panel (Add a relative, birth order, the number and line inside a symbol,
adding children to a couple, text labels), the help, keyboard shortcuts,
long entries in the key, the phone layout, and opening pedigrees saved by
earlier versions.

usage: python3 check.py [PAGE]
  PAGE  the Studio page to check (default: the index.html two folders up)

Needs Python 3 with Playwright (pip install playwright; playwright install
chromium). Exits with status 1 if any check fails."""
import json, os, sys, tempfile
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
page = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.join(HERE, '..', '..', 'index.html')
url = 'file://' + page
fails = []


def check(cond, msg):
    print(('ok   ' if cond else 'FAIL ') + msg)
    if not cond:
        fails.append(msg)


blocked = []


def watch(pg):
    """Note anything the page's Content Security Policy stops: in normal use, nothing should be."""
    pg.on('console', lambda m: blocked.append(m.text) if 'Content Security Policy' in m.text else None)
    return pg


# A pedigree saved by the Studio before this interface: S was then labelled
# "several people"; it is kept as it was drawn.
OLD_SESSION = {
    'version': 4, 'personIdCounter': 4, 'labelIdCounter': 0, 'lineIdCounter': 3,
    'persons': [
        {'id': 'person-1', 'shape': 'male', 'x': 300, 'y': 300, 'text': 'b. 1950', 'deceased': True, 'proband': False,
         'fillMode': 'solid', 'fillColor': '#1a2332', 'quarters': [None] * 4, 'centerText': ''},
        {'id': 'person-2', 'shape': 'female', 'x': 404, 'y': 300, 'text': '', 'deceased': False, 'proband': False,
         'fillMode': 'none', 'fillColor': '#1a2332', 'quarters': [None] * 4, 'centerText': 'dot'},
        {'id': 'person-3', 'shape': 'unknown', 'x': 300, 'y': 430, 'text': '', 'deceased': False, 'proband': True,
         'fillMode': 'none', 'fillColor': '#1a2332', 'quarters': [None] * 4, 'centerText': 'S'},
        {'id': 'person-4', 'shape': 'female', 'x': 404, 'y': 430, 'text': 'Breast cancer 45', 'deceased': False,
         'proband': False, 'fillMode': 'none', 'fillColor': '#1a2332', 'quarters': [None] * 4, 'centerText': ''}],
    'labels': [],
    'partnerships': [{'id': 'pship-1', 'fromId': 'person-1', 'toId': 'person-2', 'type': 'normal'}],
    'childLinks': [{'id': 'cl-2', 'partnershipId': 'pship-1', 'childId': 'person-3'},
                   {'id': 'cl-3', 'partnershipId': 'pship-1', 'childId': 'person-4'}],
    'twinLinks': [], 'legendLabels': {}, 'legendVisible': False, 'zoom': 1, 'panX': 0, 'panY': 0,
    'numberingMode': 'numbers', 'partnerGapMultiplier': 2, 'childHeightMultiplier': 2.5
}

# A pedigree whose key has a long entry, for the key's two ways of showing one
LONG_ENTRY = 'Early-onset familial Alzheimer disease, with symptoms before the age of 65'
KEY_SESSION = {
    'version': 5, 'personIdCounter': 3, 'labelIdCounter': 0, 'lineIdCounter': 2,
    'persons': [
        {'id': 'person-1', 'shape': 'male', 'x': 300, 'y': 300, 'text': '', 'deceased': False, 'proband': False,
         'fillMode': 'solid', 'fillColor': '#c0392b', 'quarters': [None] * 4, 'centerText': ''},
        {'id': 'person-2', 'shape': 'female', 'x': 404, 'y': 300, 'text': '', 'deceased': False, 'proband': False,
         'fillMode': 'solid', 'fillColor': '#2980b9', 'quarters': [None] * 4, 'centerText': ''},
        {'id': 'person-3', 'shape': 'female', 'x': 352, 'y': 430, 'text': '', 'deceased': False, 'proband': True,
         'fillMode': 'shading', 'shadingPattern': 'stripes', 'shadingCoverage': 'full', 'fillColor': '#1a2332',
         'quarters': [None] * 4, 'centerText': ''}],
    'labels': [], 'partnerships': [{'id': 'pship-1', 'fromId': 'person-1', 'toId': 'person-2', 'type': 'normal'}],
    'childLinks': [{'id': 'cl-2', 'partnershipId': 'pship-1', 'childId': 'person-3'}], 'twinLinks': [],
    'legendLabels': {'#c0392b': LONG_ENTRY, '#2980b9': 'Breast cancer', 'shading:stripes:full': 'Hearing loss'},
    'legendVisible': True, 'legendX': 520, 'legendY': 260, 'zoom': 1, 'panX': 0, 'panY': 0,
    'numberingMode': 'numbers', 'partnerGapMultiplier': 2, 'childHeightMultiplier': 2.5
}

# Things that make a pedigree say the wrong thing: symbols on top of each
# other, two couples' sibship lines running together, a child level with
# or above their parents.
PROBLEMS = """() => {
  const out = [];
  const a = Array.from(persons.values()).map(p => ({ id: p.id, x: getPersonX(p.id), y: getPersonY(p.id) }));
  for (let i = 0; i < a.length; i++) for (let j = i + 1; j < a.length; j++)
    if (Math.abs(a[i].x - a[j].x) < SHAPE_SIZE - 2 && Math.abs(a[i].y - a[j].y) < SHAPE_SIZE - 2) out.push('overlap ' + a[i].id + ' ' + a[j].id);
  const bars = [];
  childLinks.forEach(c => {
    const n = (c.els[0].getAttribute('d') || '').match(/-?[\\d.]+/g) || [];
    if (n.length >= 8) bars.push({ p: c.partnershipId, y: Math.round(+n[3]), a: Math.min(+n[2], +n[4]), b: Math.max(+n[2], +n[4]) });
  });
  for (let i = 0; i < bars.length; i++) for (let j = i + 1; j < bars.length; j++) {
    const s = bars[i], t = bars[j];
    if (s.p !== t.p && Math.abs(s.y - t.y) < 2 && Math.min(s.b, t.b) - Math.max(s.a, t.a) > 4) out.push('shared line ' + s.p + ' ' + t.p);
  }
  childLinks.forEach(c => {
    const ps = partnerships.find(p => p.id === c.partnershipId);
    if (ps && getPersonY(c.childId) <= Math.max(getPersonY(ps.fromId), getPersonY(ps.toId)) + 20) out.push('child not below ' + c.childId);
  });
  return Array.from(new Set(out));
}"""

BUILDS = [
    ['add:male', 'partner', 'parents', 'brother', 'sel:partner', 'parents', 'sister'],
    ['add:male', 'parents', 'brother', 'partner', 'sel:partner', 'parents', 'sister'],
    ['add:male', 'partner', 'son', 'daughter', 'parents', 'brother', 'sister', 'sel:partner', 'parents', 'sister'],
    ['add:female', 'parents', 'sel:father', 'parents', 'brother', 'sel:mother', 'parents', 'sister', 'sister',
     'sel:me', 'partner', 'son', 'son', 'daughter'],
    ['one-at-a-time', 'add:male', 'partner', 'son', 'daughter', 'parents', 'brother', 'sister', 'sel:partner',
     'parents', 'brother', 'partner'],
]


def build(pg, steps):
    ev = pg.evaluate
    me = None
    for st in steps:
        if st.startswith('add:'):
            pg.click('[data-add="%s"]' % st[4:])
            me = ev("() => selectedPerson")
        elif st == 'one-at-a-time':
            ev("() => { if (!individualMoveMode) toggleIndividualMove(); }")
        elif st == 'sel:me':
            ev("(id) => selectPerson(id)", me)
        elif st == 'sel:partner':
            ev("""(id) => { const ps = partnerships.find(p => (p.fromId === id || p.toId === id) && !getPartnershipChildIds(p.id).includes(id));
                  selectPerson(ps.fromId === id ? ps.toId : ps.fromId); }""", me)
        elif st in ('sel:father', 'sel:mother'):
            ev("(a) => { const ps = parentPartnershipOf(a[0]); selectPerson(a[1] ? ps.fromId : ps.toId); }", [me, st == 'sel:father'])
        else:
            pg.click('[data-qa="%s"]' % st)


with sync_playwright() as p:
    browser = p.chromium.launch()
    ctx = browser.new_context(viewport={'width': 1400, 'height': 900}, accept_downloads=True)
    pg = watch(ctx.new_page())
    errors = []
    pg.on('pageerror', lambda e: errors.append(str(e)))
    pg.on('dialog', lambda d: d.accept())
    pg.goto(url)
    pg.wait_for_timeout(300)
    pg.evaluate("() => { try { localStorage.clear(); } catch (e) {} }")
    pg.reload()
    pg.wait_for_timeout(300)
    ev = pg.evaluate
    shown = lambda sel: ev("(s) => { const e = document.querySelector(s); return !!e && e.getClientRects().length > 0; }", sel)
    count = lambda: ev("() => [persons.size, partnerships.length, childLinks.length]")
    stacks = lambda: ev("() => [undoStack.length, redoStack.length]")

    check(shown('#emptyHint') and not shown('#inspector'), 'empty canvas shows the hint and no panel')

    # the first person and their relatives
    pg.click('[data-add="male"]')
    check(count()[0] == 1 and shown('#inspector') and shown('#propsPanel'), 'Male adds a person and opens the panel')
    check(not shown('#emptyHint'), 'the hint goes once someone is drawn')
    first = ev("() => selectedPerson")
    pg.click('[data-qa="partner"]')
    check(count()[:2] == [2, 1], 'Partner adds a partner joined to them')
    pg.click('[data-qa="son"]')
    check(count() == [3, 1, 1], 'Son adds a child of the couple')
    pg.click('[data-qa="parents"]')
    check(count() == [5, 2, 2], 'Parents adds a father and mother above')
    check(ev("() => document.querySelector('[data-qa=\"parents\"]').disabled"), 'Parents is greyed out once they are there')
    before = stacks()
    ev("(id) => addRelative('parents', id)", first)
    check(count() == [5, 2, 2] and stacks() == before, '...and asking again changes nothing, not even Undo')
    pg.click('[data-qa="brother"]')
    pg.click('[data-qa="sister"]')
    check(count() == [7, 2, 4], 'Brother and Sister join the same parents')
    check(ev("() => selectedPerson") == first, 'the person stays selected while relatives are added')
    check(ev(PROBLEMS) == [], 'the drawing has no overlaps or shared lines: %s' % ev(PROBLEMS))
    pg.click('.undo-btn')
    check(count() == [6, 2, 3], 'one undo removes one added relative')
    pg.click('.redo-btn')
    check(count() == [7, 2, 4], 'redo brings it back')

    # brother for someone with no parents: parents and brother in one step
    ev("() => { deselectAll(); }")
    pg.click('[data-add="female"]')
    lone = ev("() => selectedPerson")
    pg.click('[data-qa="brother"]')
    check(count()[0] == 11, 'Brother for someone without parents adds parents too')
    pg.click('.undo-btn')
    check(count()[0] == 8 and ev("(id) => persons.has(id)", lone), '...and one undo takes all three away')
    ev("(id) => removePerson(id)", lone)

    # birth order
    ev("(id) => selectPerson(id)", first)
    check(shown('#sibMove'), 'Birth order shows for someone with brothers and sisters')
    order = "(id) => { const ps = parentPartnershipOf(id); return getPartnershipChildIds(ps.id).sort((a, b) => getPersonX(a) - getPersonX(b)); }"
    before = ev(order, first)
    i = before.index(first)
    check(ev("() => document.querySelector('[data-mv=\"-1\"]').disabled") == (i == 0), 'Older is greyed out only for the oldest')
    pg.click('[data-mv="1"]' if i < len(before) - 1 else '[data-mv="-1"]')
    after = ev(order, first)
    check(after != before and sorted(after) == sorted(before), 'Older/Younger change the order: %s -> %s' % (before, after))
    pg.click('#tidyBtn')
    pg.wait_for_timeout(200)
    check(ev(order, first) == after, 'Tidy keeps the new order')
    check('tidied' in ev("() => document.getElementById('statusBar').textContent").lower(), 'Tidy says so')

    # inside the symbol
    ev("(id) => selectPerson(id)", first)
    pg.fill('#ctNumber', '3')
    pg.click('#ctNumberBtn')
    check(ev("(id) => persons.get(id).centerText", first) == '3', 'a number goes inside the symbol')
    check(ev("() => document.getElementById('ctNumberBtn').classList.contains('active')"), '...and Number shows as chosen')
    pg.fill('#ctNumber', 'N')
    pg.press('#ctNumber', 'Enter')
    check(ev("(id) => persons.get(id).centerText", first) == 'n', 'n (any case) for a number not known')
    pg.fill('#ctNumber', 'x')
    pg.click('#ctNumberBtn')
    check(ev("(id) => persons.get(id).centerText", first) == 'n', 'anything else is refused')
    pg.click('[data-ct="line"]')
    check(ev("(id) => persons.get(id).centerText", first) == 'line', 'Presymptomatic sets a line')
    check(ev("(id) => !!persons.get(id).el.querySelector('.person-shape svg line[x1=\"26\"]')", first), '...drawn down the middle of the symbol')
    check(ev("() => document.getElementById('ctNumber').value") == '', '...and the number box empties')

    # a relationship line
    ev("() => { const ps = partnerships[0]; ps.hitEl.dispatchEvent(new MouseEvent('click', { bubbles: true })); }")
    check(shown('#partnershipPropsPanel') and not shown('#propsPanel'), 'clicking a relationship line shows its panel')
    kids = "() => getPartnershipChildIds(partnerships[0].id).length"
    n0 = ev(kids)
    pg.click('[data-qp="female"]')
    pg.click('[data-qp="no-offspring"]')
    check(ev(kids) == n0 + 2, 'Add a child adds to that couple')
    check(ev("() => persons.get(getPartnershipChildIds(partnerships[0].id).slice(-1)[0]).shape") == 'no-offspring', 'No children adds the bar symbol under the couple')
    check(shown('#partnershipPropsPanel'), '...and the couple stays selected')
    pg.click('#partnershipPropsPanel [data-pt="separated"]')
    check(ev("() => partnerships[0].type").endswith('separated'), 'Separated changes the line')
    check(ev("() => currentPartnershipType") == 'normal', '...without changing the type of the next line drawn')

    # a line symbol has a shorter panel
    ev("() => selectPerson(getPartnershipChildIds(partnerships[0].id).slice(-1)[0])")
    check(not shown('#propsPanel .qa') and not shown('#deceasedToggle') and shown('#propsPanel .only-line'), 'No children shows only what applies to it')
    check(ev("() => document.getElementById('inspTitle').textContent") == 'No children', '...under its own name')

    # tools and Esc
    pg.click('#tool-partner')
    check(ev("() => currentTool") == 'partner' and not shown('#inspector'), 'Partners tool clears the selection')
    pg.keyboard.press('Escape')
    check(ev("() => currentTool") == 'move', 'Esc goes back to Select')
    pg.click('#tool-twin')
    check(shown('#twinPanel'), 'the Twins tool shows the twin type')
    pg.click('#tool-draw')
    check(shown('#drawPanel') and not shown('#twinPanel'), 'the Draw tool shows the pen')
    pg.click('#tool-move')
    check(not shown('#inspector'), 'Select hides them again')

    # menus
    pg.click('#fileBtn')
    check(shown('#fileMenu') and ev("() => document.getElementById('fileBtn').getAttribute('aria-expanded')") == 'true', 'File opens its menu')
    check(ev("() => document.getElementById('fileMenu').contains(document.activeElement)"), '...with the keyboard in it')
    pg.keyboard.press('Escape')
    check(not shown('#fileMenu') and ev("() => document.activeElement.id") == 'fileBtn', 'Esc closes it and goes back to File')
    pg.click('#fileBtn')
    pg.click('#fileMenu .toggle-switch')
    check(ev("() => individualMoveMode") and shown('#fileMenu'), 'settings change and the menu stays open')
    check(ev("() => document.getElementById('individualMoveToggle').getAttribute('aria-checked')") == 'true', 'switches say whether they are on')
    pg.click('#fileMenu .toggle-switch')
    with pg.expect_download() as dl:
        pg.click('#fileMenu button:has-text("Save")')
    saved_path = dl.value.path()
    saved = json.load(open(saved_path))
    check(len(saved['persons']) == ev("() => persons.size") and not shown('#fileMenu'), 'Save downloads the pedigree and closes the menu')
    check(saved.get('version') == 5, 'files are saved as version 5')
    check(any(p.get('centerText') == 'line' for p in saved['persons']), 'the line inside a symbol is saved')
    with pg.expect_download() as dl:
        pg.click('#fileBtn')
        pg.click('#fileMenu button:has-text("Vector (SVG)")')
    svg = open(dl.value.path()).read()
    check('<svg' in svg and svg.count('<line') > 0, 'SVG export works')
    with pg.expect_download() as dl:
        pg.click('#fileBtn')
        pg.click('#fileMenu button:has-text("Picture (PNG)")')
    check(os.path.getsize(dl.value.path()) > 2000, 'PNG export works')
    pg.click('#moreAddBtn')
    check(shown('#moreMenu') and ev("() => document.activeElement.dataset.add") == 'no-offspring', 'More opens its menu with the keyboard on the first item')
    pg.keyboard.press('ArrowDown')
    check(ev("() => document.activeElement.dataset.add") == 'infertile', 'arrow keys move down the menu')
    pg.keyboard.press('Shift+Tab')
    pg.keyboard.press('Tab')
    for _ in range(8):
        pg.keyboard.press('Tab')
    check(not shown('#moreMenu'), 'tabbing out of the menu closes it')
    pg.click('#moreAddBtn')
    pg.click('[data-add="adopted-female"]')
    check(not shown('#moreMenu') and ev("() => persons.get(selectedPerson).shape") == 'adopted-female', 'a More symbol is added and selected')

    # keys do not reach the drawing behind the help or a menu
    sel = ev("() => selectedPerson")
    n = ev("() => persons.size")
    pg.keyboard.press('?')
    check(shown('#helpOverlay') and shown('#helpPane-start'), '? opens the help')
    pg.keyboard.press('Backspace')
    pg.keyboard.press('Control+z')
    pg.keyboard.press('Control+a')
    pg.click('#helpPane-start p')  # focus may fall on plain text
    pg.keyboard.press('Delete')
    check(ev("() => persons.size") == n and ev("() => selectedPerson") == sel, 'Delete, Backspace, Ctrl+Z and Ctrl+A do nothing to the drawing while the help is open')
    check(ev("() => document.getElementById('helpBody').tabIndex") == 0, 'the help can be scrolled from the keyboard')
    pg.click('[data-help="symbols"]')
    check(ev("() => document.querySelectorAll('#symbolTable tbody tr:not(.sym-group)').length") >= 20, 'the symbol table is filled in')
    check(ev("() => document.querySelectorAll('#toolbarKey .tk-item').length") >= 15, 'the help shows every toolbar button with its name')
    pg.keyboard.press('ArrowRight')
    check(shown('#helpPane-keys'), 'arrow keys move between the help tabs')
    pg.keyboard.press('Escape')
    check(not shown('#helpOverlay') and ev("() => selectedPerson") == sel, 'Esc closes the help and keeps the selection')
    ev("() => { if (!individualMoveMode) toggleIndividualMove(); }")
    x0 = ev("(id) => getPersonX(id)", sel)
    pg.click('#moreAddBtn')
    pg.keyboard.press('ArrowDown')
    pg.keyboard.press('ArrowRight')
    pg.keyboard.press('Backspace')
    check(ev("(id) => getPersonX(id)", sel) == x0 and ev("() => persons.size") == n, 'keys in a menu do not move or delete the person behind it')
    pg.keyboard.press('Escape')
    ev("() => { if (individualMoveMode) toggleIndividualMove(); }")

    # text labels
    pg.click('#moreAddBtn')
    pg.click('[data-add="label"]')
    check(ev("() => currentTool") == 'label', 'Text label waits for a click on the canvas')
    pg.mouse.click(120, 820)
    pg.wait_for_timeout(120)
    check(ev("() => labels.size") == 1 and ev("() => currentTool") == 'move' and shown('#labelPanel'), 'one click places a label, back to Select, label panel open')
    pg.keyboard.type('Drawn by TJH')
    pg.click('#labelPanel .size-btn:has-text("+")')
    check(ev("() => labels.get(selectedLabel).size") == 16, 'the size goes up from the label\'s own size')
    pg.click('#labelBorderToggle')
    check(ev("() => labels.get(selectedLabel).bordered") and ev("() => document.getElementById('labelBorderToggle').classList.contains('on')"), 'Border switches on')
    pg.click('#deleteLabelBtn')
    check(ev("() => labels.size") == 0 and not shown('#labelPanel'), 'Delete removes the label and its panel')

    # the panel scrolls rather than zooming the canvas
    ev("(id) => selectPerson(id)", first)
    z = ev("() => zoomLevel")
    box = pg.locator('#inspector').bounding_box()
    pg.mouse.move(box['x'] + 100, box['y'] + 100)
    pg.mouse.wheel(0, 300)
    pg.wait_for_timeout(100)
    check(ev("() => zoomLevel") == z, 'the mouse wheel over the panel does not zoom')

    pg.click('#keyBtn')
    check(ev("() => legendVisible") and ev("() => document.getElementById('keyBtn').classList.contains('on')"), 'Key shows the colour key')
    kb = pg.locator('#legend-box').bounding_box()
    ib = pg.locator('#inspector').bounding_box()
    check(kb and kb['x'] >= 0 and kb['y'] >= 52 and kb['x'] + kb['width'] <= ib['x'], '...where it can be seen')
    pg.click('#keyBtn')

    # Shift+click after a plain click selects both
    two = ev("() => Array.from(persons.keys()).slice(0, 2)")
    pg.click('#%s .person-shape' % two[0], position={'x': 10, 'y': 26})
    pg.click('#%s .person-shape' % two[1], position={'x': 10, 'y': 26}, modifiers=['Shift'])
    check(sorted(ev("() => Array.from(multiSelected)")) == sorted(two) and shown('#multiSelectPanel'), 'Shift+click adds to a single selection')
    ev("() => deselectAll()")

    # opening a file or clearing the canvas closes the panel
    ev("(id) => selectPerson(id)", first)
    pg.set_input_files('#importFile', saved_path)
    pg.wait_for_timeout(300)
    check(not shown('#inspector') and ev("() => selectedPerson") is None, 'opening a file closes the panel')
    bad = os.path.join(tempfile.mkdtemp(), 'bad.json')
    json.dump({'persons': [{'id': 'person-1', 'shape': 'male', 'x': 1, 'y': 1}], 'partnerships': [{'id': 'pship-9'}]}, open(bad, 'w'))
    pg.set_input_files('#importFile', bad)
    pg.wait_for_timeout(300)
    check(ev("() => isRestoring") is False, 'a file that cannot be read leaves Undo working')
    pg.set_input_files('#importFile', saved_path)
    pg.wait_for_timeout(300)
    pg.click('#moreAddBtn')
    pg.click('[data-add="label"]')
    pg.mouse.click(120, 820)
    pg.wait_for_timeout(120)
    pg.click('#fileBtn')
    pg.click('#fileMenu button:has-text("Clear")')
    pg.wait_for_timeout(100)
    check(not shown('#inspector') and shown('#emptyHint'), 'clearing the canvas closes the panel and shows the hint')

    # twins move together in the birth order
    ev("""() => restoreSession({ persons: [
        { id: 'person-1', shape: 'male', x: 300, y: 200 }, { id: 'person-2', shape: 'female', x: 404, y: 200 },
        { id: 'person-3', shape: 'male', x: 248, y: 330 }, { id: 'person-4', shape: 'male', x: 352, y: 330 },
        { id: 'person-5', shape: 'female', x: 456, y: 330 }],
      partnerships: [{ id: 'pship-1', fromId: 'person-1', toId: 'person-2' }],
      childLinks: [{ id: 'cl-1', partnershipId: 'pship-1', childId: 'person-3' }, { id: 'cl-2', partnershipId: 'pship-1', childId: 'person-4' },
        { id: 'cl-3', partnershipId: 'pship-1', childId: 'person-5' }],
      twinLinks: [{ id: 'twin-1', child1Id: 'person-3', child2Id: 'person-4', type: 'identical', partnershipId: 'pship-1' }] })""")
    ev("() => selectPerson('person-5')")
    pg.click('[data-mv="-1"]')
    order = ev("() => ['person-3', 'person-4', 'person-5'].sort((a, b) => getPersonX(a) - getPersonX(b))")
    check(order[0] == 'person-5', 'Older moves a child past a pair of twins, not between them: %s' % order)
    check(ev("() => document.querySelector('[data-mv=\"-1\"]').disabled"), '...and then they are the oldest')

    # Draw: black and 4 px unless the user picks otherwise, as testers asked
    pg.click('#tool-draw')
    check(shown('#drawPanel'), 'Draw shows its settings')
    check(ev("() => [drawColor, drawLineWidth]") == ['#1a2332', 4], 'Draw starts in black, 4 px wide')
    check(ev("() => { const b = Array.from(document.querySelectorAll('.draw-color-btn')); return b.filter(x => x.classList.contains('active')).length === 1 && b[0].classList.contains('active'); }"),
          '...with the black swatch chosen')
    check(ev("() => [document.getElementById('drawWidthSlider').value, document.getElementById('drawWidthLabel').textContent]") == ['4', '4px'],
          '...and the width slider at 4px')
    spot = ev("""() => { const r = document.getElementById('canvasArea').getBoundingClientRect();
        for (let fy = 0.9; fy > 0.3; fy -= 0.05) for (let fx = 0.1; fx < 0.9; fx += 0.05) {
          const x = r.left + fx * r.width, y = r.top + fy * r.height, ok = (px, py) => { const e = document.elementFromPoint(px, py);
            return !!e && (['canvasArea', 'canvas', 'lines-layer', 'draw-layer'].includes(e.id) || !!e.closest('#lines-layer') || !!e.closest('#draw-layer')); };
          if (ok(x, y) && ok(x + 60, y - 10)) return [x, y]; }
        return null; }""")
    if spot:
        n = ev("() => drawStrokes.length")
        pg.mouse.move(spot[0], spot[1])
        pg.mouse.down()
        pg.mouse.move(spot[0] + 60, spot[1] - 10, steps=6)
        pg.mouse.up()
        st = ev("() => { const s = drawStrokes[drawStrokes.length - 1]; return [drawStrokes.length, s.color, s.width, s.el.getAttribute('stroke'), s.el.getAttribute('stroke-width')]; }")
        check(st == [n + 1, '#1a2332', 4, '#1a2332', '4'], 'a stroke drawn is black and 4 px wide: %s' % st)
        pg.click('.undo-btn')
        check(ev("() => drawStrokes.length") == n, '...and undo takes it away')
    else:
        check(False, 'found an empty spot on the canvas to draw on')
    ev("() => { setDrawColor('#2980b9'); setDrawWidth(7); }")
    check(ev("() => [drawColor, drawLineWidth, document.getElementById('drawWidthLabel').textContent]") == ['#2980b9', 7, '7px'],
          '...and the colour and width can still be changed')
    ev("() => { setDrawColor('#1a2332'); setDrawWidth(4); document.getElementById('drawWidthSlider').value = 4; }")
    pg.click('#tool-move')

    # pedigrees from earlier versions
    ev("(d) => { restoreSession(d); updateAllConnections(); }", OLD_SESSION)
    pg.wait_for_timeout(100)
    check(ev("() => persons.size") == 4 and ev("() => persons.get('person-3').centerText") == 'S', 'an older pedigree opens unchanged')
    check('>S<' in ev("() => persons.get('person-3').el.innerHTML"), '...and its S is still drawn')
    ev("() => selectPerson('person-3')")
    check(ev("() => !document.querySelector('[data-ct=\"S\"]') && !!document.querySelector('[data-ct=\"G\"]')"
             " && !document.querySelector('[data-ct].active') && persons.get('person-3').centerText === 'S'"),
          '...and the panel, which offers G in its place since the 2025 correction, leaves its S as it is')

    # long entries in the key: they widen it, or, as File sets, wrap onto more lines in a key whose width can be
    # dragged; the exports show the key as it is
    ev("(d) => restoreSession(d)", KEY_SESSION)
    pg.wait_for_timeout(150)
    fields = """() => Array.from(document.querySelectorAll('#legend-box .legend-input')).map(f => ({
        tag: f.tagName, sw: f.scrollWidth, cw: f.clientWidth, sh: f.scrollHeight, ch: f.clientHeight, w: f.offsetWidth }))"""
    key_width = lambda: pg.locator('#legend-box').bounding_box()['width']
    f = ev(fields)
    check(ev("() => legendFit") == 'widen' and all(x['tag'] == 'INPUT' and x['sw'] <= x['cw'] + 1 for x in f) and key_width() > 400,
          'a long entry in the key widens it, and every entry shows all its text')
    check(len(set(x['w'] for x in f)) == 1, '...with the entries lined up')
    pg.click('#fileBtn')
    pg.click('[data-lf="wrap"]')
    check(ev("() => legendFit") == 'wrap' and shown('#fileMenu'), 'File sets long entries to wrap, and stays open')
    pg.keyboard.press('Escape')
    f = ev(fields)
    check(all(x['tag'] == 'TEXTAREA' and x['sh'] <= x['ch'] + 1 for x in f) and abs(key_width() - 240) < 1 and f[0]['ch'] > 2 * f[1]['ch'] - 10,
          '...then the key keeps its width, and the long entry takes more lines')
    g = pg.locator('#legend-box .legend-resize').bounding_box()
    pg.mouse.move(g['x'] + g['width'] / 2, g['y'] + g['height'] / 2)
    pg.mouse.down()
    pg.mouse.move(g['x'] + g['width'] / 2 + 120, g['y'] + g['height'] / 2, steps=5)
    pg.mouse.up()
    check(abs(ev("() => legendWidth") - 360) <= 2 and abs(key_width() - ev("() => legendWidth")) < 1 and ev("() => [legendX, legendY]") == [520, 260],
          "dragging the key's right edge widens it, without moving it")
    pg.keyboard.press('Control+z')
    check(ev("() => legendWidth") == 240, '...and undo narrows it again')
    pg.keyboard.press('Control+y')
    saved = ev("() => buildSessionData()")
    check(saved.get('legendFit') == 'wrap' and saved.get('legendWidth') == 360, 'how long entries show, and the width, are saved')
    ev("(d) => restoreSession(d)", saved)
    check(ev("() => legendFit") == 'wrap' and abs(key_width() - 360) < 1 and ev("() => document.querySelector('[data-lf=wrap]').classList.contains('active')"),
          '...and come back when the pedigree is opened')
    # (KEY, then the entries: the long one takes two lines in a key 360 pixels wide)
    for mode in ('wrap', 'widen'):
        ev("(m) => setLegendFit(m)", mode)
        with pg.expect_download() as dl:
            ev("() => saveAsSVG()")
        svg = open(dl.value.path(), encoding='utf-8').read()
        drawn = ev("""(svg) => {
            const host = document.createElement('div'); host.innerHTML = svg; document.body.appendChild(host);
            const s = host.querySelector('svg'), rects = Array.from(s.querySelectorAll('rect[rx="8"]'));
            const key = rects[rects.length - 1].getBBox();
            const lines = Array.from(s.querySelectorAll('text')).map(t => [t.textContent, t.getBBox()])
              .filter(([, b]) => b.x >= key.x && b.y >= key.y && b.y <= key.y + key.height);
            host.remove();
            return { inside: lines.every(([, b]) => b.x + b.width <= key.x + key.width + 0.5 && b.y + b.height <= key.y + key.height + 0.5),
                     text: lines.map(([t]) => t).join(' '), n: lines.length }; }""", svg)
        check(drawn['inside'] and LONG_ENTRY in drawn['text'] and drawn['n'] == (4 if mode == 'widen' else 5),
              'the SVG export shows the key as it is, every word inside it, when entries %s (%d lines)' % ('widen it' if mode == 'widen' else 'wrap', drawn['n']))
    ev("(d) => restoreSession(d)", OLD_SESSION)
    check(ev("() => legendFit") == 'widen', 'a pedigree saved before this setting widens its key')

    check(not errors, 'no errors on the page: %s' % errors[:3])
    ctx.close()

    # pedigrees built only with Add a relative read correctly at every size of family
    for steps in BUILDS:
        ctx = browser.new_context(viewport={'width': 1400, 'height': 900})
        pg = watch(ctx.new_page())
        pg.on('dialog', lambda d: d.accept())
        pg.goto(url)
        pg.wait_for_timeout(200)
        pg.evaluate("() => { try { localStorage.clear(); } catch (e) {} }")
        build(pg, steps)
        probs = pg.evaluate(PROBLEMS)
        check(probs == [], 'built with Add a relative (%s): %s' % (' '.join(steps), probs or 'reads correctly'))
        ctx.close()

    # phone
    ctx = browser.new_context(viewport={'width': 390, 'height': 844}, has_touch=True, is_mobile=True)
    pg = watch(ctx.new_page())
    errors = []
    pg.on('pageerror', lambda e: errors.append(str(e)))
    pg.goto(url)
    pg.wait_for_timeout(300)
    pg.evaluate("() => { try { localStorage.clear(); } catch (e) {} }")
    pg.tap('[data-add="female"]')
    pg.tap('[data-qa="parents"]')
    box = pg.locator('#inspector').bounding_box()
    check(box and box['width'] > 360 and box['y'] + box['height'] > 700, 'on a phone the panel is a sheet along the bottom')
    bar = pg.locator('.st-bar').bounding_box()
    check(bar['height'] < 100, 'on a phone the toolbar fits in two rows (%dpx)' % bar['height'])
    wide = pg.evaluate("() => document.documentElement.scrollWidth")
    check(wide <= 390, 'nothing is wider than the phone (%dpx)' % wide)
    pg.tap('[data-mv="1"]') if pg.evaluate("() => !document.querySelector('[data-mv=\"1\"]').disabled") else None
    pg.fill('#ctNumber', 'x')
    pg.tap('#ctNumberBtn')
    pg.wait_for_timeout(100)
    toast = pg.locator('#statusBar')
    check(toast.evaluate("e => getComputedStyle(e).opacity") == '1' and 'number' in toast.inner_text().lower(), 'on a phone messages show above the panel')
    # tap someone the panel would cover
    pg.evaluate("() => deselectAll()")
    pg.wait_for_timeout(100)
    low = pg.evaluate("""() => { let best = null, bottom = 0; persons.forEach(p => { const r = p.el.querySelector('.person-shape').getBoundingClientRect();
        if (r.bottom < innerHeight - 60 && r.top > 100 && r.bottom > bottom) { bottom = r.bottom; best = p.id; } }); return best; }""")
    pg.evaluate("(id) => { panY += innerHeight - 120 - persons.get(id).el.getBoundingClientRect().bottom; applyTransform(); }", low)
    pg.tap('#%s .person-shape' % low)
    pg.wait_for_timeout(250)
    a = pg.locator('#%s .person-shape' % low).bounding_box()
    b = pg.locator('#inspector').bounding_box()
    check(a['y'] + a['height'] <= b['y'], 'tapping someone low on the screen keeps them above the panel')
    pg.tap('#helpBtn')
    hb = pg.locator('.help-card').bounding_box()
    check(abs(hb['width'] - 390) < 2, 'the help fills the phone screen')
    check(not errors, 'no errors on the phone: %s' % errors[:3])
    ctx.close()

    # the nomenclature's marks: the proband's P, a consultand's arrow, twins whose zygosity is not known,
    # G for a gestational carrier (2025 correction) and an ectopic pregnancy's slash in the help
    ctx = browser.new_context(viewport={'width': 1400, 'height': 900}, accept_downloads=True)
    pg = watch(ctx.new_page())
    errors = []
    pg.on('pageerror', lambda e: errors.append(str(e)))
    pg.on('dialog', lambda d: d.accept())
    pg.goto(url)
    pg.wait_for_timeout(300)
    pg.evaluate("() => { try { localStorage.clear(); } catch (e) {} }")
    pg.reload()
    pg.wait_for_timeout(300)
    ev = pg.evaluate
    family = {'version': 5, 'personIdCounter': 4, 'lineIdCounter': 3, 'persons': [
        {'id': 'person-1', 'shape': 'male', 'x': 300, 'y': 200}, {'id': 'person-2', 'shape': 'female', 'x': 420, 'y': 200},
        {'id': 'person-3', 'shape': 'male', 'x': 300, 'y': 360}, {'id': 'person-4', 'shape': 'male', 'x': 420, 'y': 360}],
        'partnerships': [{'id': 'pship-1', 'fromId': 'person-1', 'toId': 'person-2'}],
        'childLinks': [{'id': 'child-2', 'partnershipId': 'pship-1', 'childId': 'person-3'},
                       {'id': 'child-3', 'partnershipId': 'pship-1', 'childId': 'person-4'}]}
    ev("(d) => { restoreSession(d); fitToView(); }", family)
    arrow = lambda pid: ev("(id) => { const a = document.querySelector('#' + id + ' .proband-arrow'); return a ? (a.querySelector('text') ? 'P' : 'arrow') : ''; }", pid)
    ev("() => selectPerson('person-3')")
    pg.click('#probandToggle')
    check(arrow('person-3') == 'P', 'Proband draws the arrow with a P')
    ev("() => selectPerson('person-2')")
    pg.click('#consultandToggle')
    check(arrow('person-2') == 'arrow' and ev("() => document.getElementById('consultandToggle').classList.contains('on')"),
          'Consultand draws the arrow alone, and the switch shows it')
    ev("() => selectPerson('person-1')")
    pg.click('#consultandToggle')
    check(arrow('person-1') == 'arrow' and arrow('person-2') == 'arrow', 'there can be more than one consultand')
    ev("() => selectPerson('person-4')")
    pg.click('#probandToggle')
    check(arrow('person-4') == 'P' and arrow('person-3') == '', 'there is one proband: marking another moves the arrow and P')
    pg.click('.undo-btn')
    check(arrow('person-3') == 'P' and arrow('person-4') == '', 'Undo moves them back')
    ev("() => deselectAll()")
    pg.click('#tool-twin')
    pg.click('[data-tt="unknown"]')
    pg.click('#person-3 .person-shape', position={'x': 26, 'y': 26})
    pg.click('#person-4 .person-shape', position={'x': 26, 'y': 26})
    pg.wait_for_timeout(150)
    mark = ev("""() => { const m = document.querySelector('#lines-layer .twin-mark');
        if (!m) return null; const r = m.getBoundingClientRect(), a = document.querySelector('#person-3').getBoundingClientRect(),
        b = document.querySelector('#person-4').getBoundingClientRect();
        return { text: m.textContent, between: r.left > a.left && r.right < b.right && r.bottom < a.top, type: twinLinks[0] && twinLinks[0].type }; }""")
    check(bool(mark) and mark['text'] == '?' and mark['between'] and mark['type'] == 'unknown',
          'Twins with Not known join the twins with a question mark between their lines: %s' % mark)
    pg.click('#tool-move')
    ev("() => selectPerson('person-2')")
    check(not shown('[data-ct="S"]') and shown('[data-ct="G"]'), 'Inside the symbol offers G for a gestational carrier, and no S')
    pg.click('[data-ct="G"]')
    check(ev("() => document.querySelector('#person-2 .person-shape text').textContent") == 'G', 'G goes inside the symbol')
    with pg.expect_download() as dl:
        ev("() => saveAsSVG()")
    svg = open(dl.value.path(), encoding='utf-8').read()
    check('>P</text>' in svg and '>?</text>' in svg and '>G</text>' in svg, 'the SVG export draws the P, the question mark and the G')
    with pg.expect_download() as dl:
        ev("() => exportJSON()")
    saved_path2 = dl.value.path()
    ev("() => restoreSession({ version: 5, persons: [] })")
    pg.set_input_files('#importFile', saved_path2)
    pg.wait_for_timeout(300)
    check(arrow('person-3') == 'P' and arrow('person-1') == 'arrow' and arrow('person-2') == 'arrow'
          and ev("() => twinLinks.length === 1 && twinLinks[0].type === 'unknown' && !!document.querySelector('#lines-layer .twin-mark')"),
          'saved and opened again, the proband, consultands and twins are as they were')
    ev("() => openHelp('symbols')") if ev("() => typeof openHelp === 'function'") else pg.click('#helpBtn')
    names = ev("() => Array.from(document.querySelectorAll('#symbolTable .sym-name')).map(e => e.textContent)")
    ect = ev("() => Array.from(document.querySelectorAll('#symbolTable tr')).find(r => /Pregnancy loss/.test(r.textContent)).textContent")
    check('Proband, consultand' in names and 'Twins, zygosity not known' in names and 'Donor, gestational carrier' in names
          and 'ectopic pregnancy, with ECT' in ect, 'the help shows the consultand, unknown zygosity, G and the ectopic slash')
    check(not errors, 'no errors with the new marks: %s' % errors[:3])
    ctx.close()

    # a link to the help
    pg = watch(browser.new_page())
    pg.goto(url + '#help')
    pg.wait_for_timeout(300)
    check(pg.evaluate("() => !document.getElementById('helpOverlay').hidden"), 'a link ending #help opens the help')
    browser.close()

check(not blocked, 'the Content Security Policy stopped nothing the Studio does: %s' % blocked[:2])
print('\n%d failed' % len(fails) if fails else '\nall passed')
sys.exit(1 if fails else 0)
