"""Random pedigrees, odd ones included (partners from different generations,
children linked to the wrong generation, people who are their own ancestors,
free-position people, twins). Checks that Tidy never fails, never leaves a
position undefined, never puts one symbol on top of another, and keeps
children below their parents wherever the relationships allow it.

usage: python3 fuzz.py [N] [FIRST_SEED] [PAGE]
Failing cases are saved as fuzz_<seed>.json to load into the Studio."""
import json, os, random, sys
from playwright.sync_api import sync_playwright
HERE = os.path.dirname(os.path.abspath(__file__))
N = int(sys.argv[1]) if len(sys.argv) > 1 else 200
seed0 = int(sys.argv[2]) if len(sys.argv) > 2 else 1
page = os.path.abspath(sys.argv[3]) if len(sys.argv) > 3 else os.path.join(HERE, '..', '..', 'index.html')

def make(seed):
    rnd = random.Random(seed)
    n = rnd.randint(1, 60)
    persons, parts, links, twins = [], [], [], []
    gens = {}
    for i in range(n):
        g = rnd.randint(0, 4)
        pid = 'p%d' % i
        gens[pid] = g
        persons.append(dict(id=pid, shape=rnd.choice(['male', 'female', 'unknown', 'male', 'female', 'miscarriage', 'adopted-male']), x=round(rnd.uniform(0, 1500), 1), y=round(160 + g * 130 + rnd.uniform(-30, 30), 1),
            text=rnd.choice(['', '', '', 'note', 'two\nlines', 'a much longer note about this person']), deceased=rnd.random() < 0.2, proband=(i == 0),
            fillMode='none', fillColor='#1a2332', quarters=[None]*4, halves=[None, None], shadingPattern='stripes', shadingCoverage='full', centerText='', miscarriageSex='unknown',
            noSnap=rnd.random() < 0.05, siblingFixed=False, customLabel='Lbl'))
    ids = [p['id'] for p in persons]
    k = 0
    pairs = set()
    for _ in range(rnd.randint(0, n)):
        a, b = rnd.sample(ids, 2) if len(ids) > 1 else (None, None)
        if a is None or (a, b) in pairs or (b, a) in pairs: continue
        # mostly same generation, sometimes not (weird)
        if gens[a] != gens[b] and rnd.random() < 0.8: continue
        pairs.add((a, b)); k += 1
        parts.append(dict(id='pship-%d' % k, fromId=a, toId=b, type=rnd.choice(['normal', 'normal', 'separated', 'consanguineous'])))
    has_parent = set()
    for ps in parts:
        for c in ids:
            if c in has_parent or c in (ps['fromId'], ps['toId']): continue
            if rnd.random() < 0.08 and (gens[c] > max(gens[ps['fromId']], gens[ps['toId']]) or rnd.random() < 0.05):
                k += 1
                links.append(dict(id='child-%d' % k, partnershipId=ps['id'], childId=c, branchYOffset=0, dashed=rnd.random() < 0.1))
                has_parent.add(c)
    # twins among siblings
    by = {}
    for l in links: by.setdefault(l['partnershipId'], []).append(l['childId'])
    for pid, kids in by.items():
        if len(kids) >= 2 and rnd.random() < 0.3:
            k += 1
            twins.append(dict(id='twin-%d' % k, child1Id=kids[0], child2Id=kids[1], type='identical', partnershipId=pid))
    return dict(version=4, personIdCounter=n, labelIdCounter=0, lineIdCounter=k, persons=persons, labels=[], partnerships=parts, childLinks=links, twinLinks=twins,
                legendLabels={}, legendVisible=False, legendX=100, legendY=100, numberingMode='numbers', partnerGapMultiplier=2, childHeightMultiplier=2.5, drawStrokes=[])

def has_loop(d):
    ps = {p['id']: p for p in d['partnerships']}
    g = {}
    for c in d['childLinks']:
        q = ps[c['partnershipId']]
        for par in (q['fromId'], q['toId']):
            g.setdefault(par, set()).add(c['childId'])
    state = {}
    def visit(u):
        state[u] = 1
        for v in g.get(u, ()):
            if state.get(v) == 1 or (not state.get(v) and visit(v)):
                return True
        state[u] = 2
        return False
    return any(visit(u) for u in list(g) if not state.get(u))

CHECK = """(d) => {
  restoreSession(d); updateAllConnections();
  let err = null;
  try { runManagedPedigreeLayout({ seedIds: Array.from(persons.keys()), reason: 'manualRedistribute', fromButton: true, fresh: true }); }
  catch (e) { err = String(e && e.stack || e); }
  const P = Array.from(persons.values()).map(p => ({ id: p.id, x: parseFloat(p.el.style.left), y: parseFloat(p.el.style.top), pin: !!p.noSnap }));
  const bad = P.filter(p => !isFinite(p.x) || !isFinite(p.y)).map(p => p.id);
  let overlaps = 0;
  for (let i = 0; i < P.length; i++) for (let j = i + 1; j < P.length; j++) {
    const a = P[i], b = P[j];
    if (a.pin || b.pin) continue;
    if (Math.abs(a.x - b.x) < SHAPE_SIZE - 1 && Math.abs(a.y - b.y) < SHAPE_SIZE - 1) overlaps++;
  }
  // children below parents (where the relationships allow it)
  let above = 0;
  childLinks.forEach(cl => {
    const ps = partnerships.find(q => q.id === cl.partnershipId); if (!ps) return;
    const a = persons.get(ps.fromId), b = persons.get(ps.toId), c = persons.get(cl.childId);
    if (!a || !b || !c || c.noSnap || a.noSnap || b.noSnap) return;
    if (parseFloat(c.el.style.top) <= Math.max(parseFloat(a.el.style.top), parseFloat(b.el.style.top))) above++;
  });
  return { err, bad, overlaps, above, n: P.length };
}"""
with sync_playwright() as p:
    br = p.chromium.launch(); pg = br.new_page()
    errors = []
    pg.on('pageerror', lambda e: errors.append(str(e)))
    pg.on('dialog', lambda d: d.accept())
    pg.goto('file://' + page); pg.wait_for_timeout(300)
    pg.evaluate("() => { try { dismissSplash(); } catch (e) {} }")
    probs = 0
    for s in range(seed0, seed0 + N):
        d = make(s)
        errors.clear()
        r = pg.evaluate(CHECK, d)
        # children level with or above a parent are expected only when someone
        # is their own ancestor (the rows are then kept as drawn)
        if r['err'] or r['bad'] or r['overlaps'] or errors or (r['above'] and not has_loop(d)):
            probs += 1
            print('seed', s, 'people', r['n'], 'err', (r['err'] or '')[:300], 'nan', r['bad'][:5], 'overlaps', r['overlaps'], 'child-not-below', r['above'], 'pageerrors', errors[:2])
            json.dump(d, open(os.path.join(HERE, 'fuzz_%d.json' % s), 'w'))
    br.close()
print('done', N, 'problems', probs)
