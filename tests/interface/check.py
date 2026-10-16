"""Checks of the Studio's interface: the toolbar and its menus, the selection
panel (Add a relative, birth order, the number and line inside a symbol,
adding children to a couple, text labels), the help, keyboard shortcuts,
the phone layout, and opening pedigrees saved by earlier versions.

usage: python3 check.py [PAGE]
  PAGE  the Studio page to check (default: the index.html two folders up)

Needs Python 3 with Playwright (pip install playwright; playwright install
chromium). Exits with status 1 if any check fails."""
import json, os, sys
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
page = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.join(HERE, '..', '..', 'index.html')
url = 'file://' + page
fails = []


def check(cond, msg):
    print(('ok   ' if cond else 'FAIL ') + msg)
    if not cond:
        fails.append(msg)


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

with sync_playwright() as p:
    browser = p.chromium.launch()
    ctx = browser.new_context(viewport={'width': 1400, 'height': 900}, accept_downloads=True)
    pg = ctx.new_page()
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
    pg.click('[data-qa="parents"]')
    check(count() == [5, 2, 2], 'Parents does nothing when they are there already')
    pg.click('[data-qa="brother"]')
    pg.click('[data-qa="sister"]')
    check(count() == [7, 2, 4], 'Brother and Sister join the same parents')
    check(ev("() => selectedPerson") == first, 'the person stays selected while relatives are added')
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
    pg.click('#partnershipPropsPanel [data-pt="separated"]')
    check(ev("() => partnerships[0].type").endswith('separated'), 'Separated changes the line')
    check(ev("() => currentPartnershipType") == 'normal', '...without changing the type of the next line drawn')

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
    pg.keyboard.press('Escape')
    check(not shown('#fileMenu'), 'Esc closes it')
    pg.click('#fileBtn')
    pg.click('#fileMenu .toggle-switch')
    check(ev("() => individualMoveMode") and shown('#fileMenu'), 'settings change and the menu stays open')
    pg.click('#fileMenu .toggle-switch')
    with pg.expect_download() as dl:
        pg.click('#fileMenu button:has-text("Save")')
    saved = json.load(open(dl.value.path()))
    check(len(saved['persons']) == ev("() => persons.size") and not shown('#fileMenu'), 'Save downloads the pedigree and closes the menu')
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
    check(shown('#moreMenu'), 'More opens its menu')
    pg.click('[data-add="adopted-female"]')
    check(not shown('#moreMenu') and ev("() => persons.get(selectedPerson).shape") == 'adopted-female', 'a More symbol is added and selected')

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

    # help
    pg.keyboard.press('?')
    check(shown('#helpOverlay') and shown('#helpPane-start'), '? opens the help')
    pg.click('[data-help="symbols"]')
    check(ev("() => document.querySelectorAll('#symbolTable tbody tr:not(.sym-group)').length") >= 20, 'the symbol table is filled in')
    pg.keyboard.press('ArrowRight')
    check(shown('#helpPane-keys'), 'arrow keys move between the help tabs')
    pg.keyboard.press('Escape')
    check(not shown('#helpOverlay') and ev("() => selectedPerson") == first, 'Esc closes the help and keeps the selection')
    pg.click('#keyBtn')
    check(ev("() => legendVisible") and ev("() => document.getElementById('keyBtn').classList.contains('on')"), 'Key shows the colour key')
    pg.click('#keyBtn')

    # pedigrees from earlier versions
    ev("(d) => { restoreSession(d); updateAllConnections(); }", OLD_SESSION)
    pg.wait_for_timeout(100)
    check(ev("() => persons.size") == 4 and ev("() => persons.get('person-3').centerText") == 'S', 'an older pedigree opens unchanged')
    check('>S<' in ev("() => persons.get('person-3').el.innerHTML"), '...and its S is still drawn')
    ev("() => selectPerson('person-3')")
    check(ev("() => document.querySelector('[data-ct=\"S\"]').classList.contains('active')"), '...and shows as S in the panel')

    check(not errors, 'no errors on the page: %s' % errors[:3])
    ctx.close()

    # phone
    ctx = browser.new_context(viewport={'width': 390, 'height': 844}, has_touch=True, is_mobile=True)
    pg = ctx.new_page()
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
    pg.tap('#helpBtn')
    hb = pg.locator('.help-card').bounding_box()
    check(abs(hb['width'] - 390) < 2, 'the help fills the phone screen')
    check(not errors, 'no errors on the phone: %s' % errors[:3])
    ctx.close()

    # a link to the help
    pg = browser.new_page()
    pg.goto(url + '#help')
    pg.wait_for_timeout(300)
    check(pg.evaluate("() => !document.getElementById('helpOverlay').hidden"), 'a link ending #help opens the help')
    browser.close()

print('\n%d failed' % len(fails) if fails else '\nall passed')
sys.exit(1 if fails else 0)
