"""Compare two or more runs, pedigree by pedigree.

usage: python3 compare.py OLD NEW [...] [--detail] [--changed]
  OLD, NEW  folder names under out/ (as given to run.py --out)
  --detail  list what the last run's score is made of
  --changed only show pedigrees whose score differs"""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
tags = [a for a in sys.argv[1:] if not a.startswith('--')]
detail, changed = '--detail' in sys.argv, '--changed' in sys.argv
res = {t: json.load(open(os.path.join(HERE, 'out', t, 'results.json'))) for t in tags}
names = [n for n in json.load(open(os.path.join(HERE, 'fixtures', 'index.json'))) if all(n in res[t] for t in tags)]
keys = [('overlap', 'overlap'), ('textOverlap', 'notes'), ('partnerRowMismatch', 'partners-apart'), ('partnerBlocked', 'line-behind'),
        ('childNotBelow', 'child-not-below'), ('crossings', 'crossings'), ('collinear', 'lines-along'), ('linesThroughSymbols', 'line-through'),
        ('sibshipIntruders', 'strangers'), ('twinsApart', 'twins-apart'), ('siblingInversions', 'order'), ('dropOutside', 'drop-outside'),
        ('misaligned', 'off-centre'), ('rowSplit', 'sibs-split'), ('numberOverlap', 'numbers'), ('numberLines', 'line-on-number')]
print('%-40s' % 'pedigree' + ''.join('%10s' % t for t in tags))
tot = {t: 0 for t in tags}
for n in names:
    sc = [res[t][n]['score'] for t in tags]
    for t, v in zip(tags, sc): tot[t] += v
    if changed and len(set(sc)) == 1:
        continue
    line = '%-40s' % n.replace('.json', '') + ''.join('%10d' % v for v in sc)
    if detail:
        r = res[tags[-1]][n]
        line += '   ' + ' '.join('%s %d' % (label, r[k]) for k, label in keys if r.get(k))
        if r.get('error') or r.get('pageErrors'): line += '  ERROR'
    print(line)
print('%-40s' % 'TOTAL' + ''.join('%10d' % tot[t] for t in tags))
