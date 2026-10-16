"""Test pedigrees for the Tidy layout, written as Pedigree Studio sessions.

Each family below is written in up to three starting states:
  neat     - roughly where a careful person would draw everyone
  messy    - the neat drawing nudged about at random
  scramble - everyone dropped at random places (the worst case)

The families in practical.json (from the pedigree practical) are added in
the same three states. Run this file to (re)write fixtures/.
"""
import json, os, random, sys

UNIT = 104          # partner gap (2 x 52)
ROW = 130           # generation gap (2.5 x 52)
X0, Y0 = 200, 160
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fixtures')


class Ped:
    def __init__(self, name, desc):
        self.name, self.desc = name, desc
        self.people = {}
        self.order = []
        self.couples = []
        self.kids = []
        self.twins = []
        self.n = 0

    def p(self, pid, sex, gen, x, text='', **f):
        assert pid not in self.people, pid
        self.people[pid] = dict(sex=sex, gen=gen, x=x, text=text, **f)
        self.order.append(pid)
        return pid

    def c(self, a, b, typ='normal'):
        self.n += 1
        cid = 'pship-%d' % self.n
        self.couples.append((cid, a, b, typ))
        return cid

    def k(self, cid, kids, dashed=()):
        self.kids.append((cid, list(kids), set(dashed)))

    def t(self, a, b, typ='identical'):
        self.twins.append((a, b, typ))

    # -- output ---------------------------------------------------------
    def session(self, state='neat', seed=1):
        rnd = random.Random(seed)
        persons = []
        pos = {}
        for pid in self.order:
            d = self.people[pid]
            x, y = X0 + d['x'] * UNIT, Y0 + d['gen'] * ROW
            if state == 'messy':
                x += rnd.uniform(-60, 60)
                y += rnd.uniform(-25, 25)
            elif state == 'scramble':
                x = rnd.uniform(0, 1400)
                y = rnd.uniform(0, 900)
            pos[pid] = (round(x, 1), round(y, 1))
        for pid in self.order:
            d = self.people[pid]
            sex = d['sex']
            shape = {'M': 'male', 'F': 'female', 'U': 'unknown'}[sex]
            if d.get('adopted'):
                shape = 'adopted-' + shape
            if d.get('loss'):
                shape = 'miscarriage'
            if d.get('line'):
                shape = d['line']
            x, y = pos[pid]
            persons.append(dict(
                id=pid, shape=shape, x=x, y=y, text=d.get('text', ''),
                deceased=bool(d.get('deceased')), proband=bool(d.get('proband')),
                fillMode='solid' if d.get('affected') else 'none', fillColor='#1a2332',
                quarters=[None] * 4, halves=[None, None], shadingPattern='stripes', shadingCoverage='full',
                centerText=d.get('centre', ''), miscarriageSex='unknown',
                noSnap=bool(d.get('pin')), siblingFixed=False, customLabel='Lbl'))
        n = self.n
        child_links = []
        for cid, kids, dashed in self.kids:
            for kid in kids:
                n += 1
                child_links.append(dict(id='child-%d' % n, partnershipId=cid, childId=kid, branchYOffset=0, dashed=kid in dashed))
        twin_links = []
        for a, b, typ in self.twins:
            n += 1
            pid = next(cid for cid, kids, _ in self.kids if a in kids)
            twin_links.append(dict(id='twin-%d' % n, child1Id=a, child2Id=b, type=typ, partnershipId=pid))
        return dict(
            version=4, personIdCounter=0, labelIdCounter=0, lineIdCounter=n,
            persons=persons, labels=[],
            partnerships=[dict(id=cid, fromId=a, toId=b, type=t) for cid, a, b, t in self.couples],
            childLinks=child_links, twinLinks=twin_links,
            legendLabels={}, legendVisible=False, legendX=100, legendY=100,
            numberingMode='numbers', partnerGapMultiplier=2, childHeightMultiplier=2.5, drawStrokes=[],
            _meta=dict(name=self.name, desc=self.desc, state=state))


S = []


def ped(name, desc):
    p = Ped(name, desc)
    S.append(p)
    return p


# 01 nuclear family
p = ped('01-nuclear', 'A couple and three children')
p.p('f', 'M', 0, 0); p.p('m', 'F', 0, 1)
c = p.c('f', 'm')
for i, s in enumerate('MFM'):
    p.p('k%d' % i, s, 1, -0.5 + i)
p.k(c, ['k0', 'k1', 'k2'])

# 02 three generations, both sets of grandparents
p = ped('02-both-sides', 'Paternal and maternal grandparents, parents and proband')
p.p('pgf', 'M', 0, 0); p.p('pgm', 'F', 0, 1); c1 = p.c('pgf', 'pgm')
p.p('pu', 'M', 1, -0.5, 'uncle, 60'); p.p('pa', 'F', 1, 0.5, 'aunt, 58'); p.p('dad', 'M', 1, 1.5, 'Dad, 55')
p.k(c1, ['pu', 'pa', 'dad'])
p.p('mgf', 'M', 0, 3.5); p.p('mgm', 'F', 0, 4.5); c2 = p.c('mgf', 'mgm')
p.p('mum', 'F', 1, 2.5, 'Mum, 53'); p.p('mu1', 'M', 1, 3.5); p.p('mu2', 'F', 1, 4.5)
p.k(c2, ['mum', 'mu1', 'mu2'])
c3 = p.c('dad', 'mum')
p.p('s1', 'F', 2, 1, 'sister, 30'); p.p('pr', 'M', 2, 2, 'proband, 28', proband=True); p.p('s2', 'M', 2, 3)
p.k(c3, ['s1', 'pr', 's2'])

# 03 a big sibship with spouses and children
p = ped('03-big-sibship', 'Twelve siblings, most married with children')
p.p('gf', 'M', 0, 5); p.p('gm', 'F', 0, 6); c = p.c('gf', 'gm')
kids = []
x = 0
rnd = random.Random(3)
for i in range(12):
    sid = 's%d' % i
    sex = 'M' if i % 2 == 0 else 'F'
    p.p(sid, sex, 1, x, 'sibling %d, %d' % (i + 1, 70 - i * 2))
    kids.append(sid)
    if i % 3 != 2:
        sp = 'sp%d' % i
        if sex == 'M':
            p.p(sp, 'F', 1, x + 1)
            cc = p.c(sid, sp)
        else:
            p.p(sp, 'M', 1, x + 1)
            cc = p.c(sp, sid)
        nk = [0, 1, 2, 3][rnd.randint(0, 3)]
        gk = []
        for j in range(nk):
            gid = 'g%d_%d' % (i, j)
            p.p(gid, 'MF'[j % 2], 2, x + j * 0.8)
            gk.append(gid)
        if gk:
            p.k(cc, gk)
        x += 2.2
    else:
        x += 1.2
p.k(c, kids)

# 04 a man with two wives (half-siblings) and his parents
p = ped('04-half-sibs', 'A man with two partners, children from each, and his parents')
p.p('gf', 'M', 0, 1); p.p('gm', 'F', 0, 2); c0 = p.c('gf', 'gm')
p.p('w1', 'F', 1, 0, 'first wife'); p.p('man', 'M', 1, 1, 'Tom, 60'); p.p('w2', 'F', 1, 2, 'second wife'); p.p('bro', 'M', 1, 3)
p.k(c0, ['man', 'bro'])
c1 = p.c('w1', 'man', 'separated'); c2 = p.c('man', 'w2')
p.p('a1', 'F', 2, -0.5); p.p('a2', 'M', 2, 0.5)
p.p('b1', 'M', 2, 1.5); p.p('b2', 'F', 2, 2.5); p.p('b3', 'F', 2, 3.5)
p.k(c1, ['a1', 'a2']); p.k(c2, ['b1', 'b2', 'b3'])

# 05 a woman with three partners
p = ped('05-three-partners', 'A woman with three partners and children by each')
p.p('w', 'F', 0, 2, 'Ann, 55', proband=True)
p.p('m1', 'M', 0, 0); p.p('m2', 'M', 0, 3); p.p('m3', 'M', 0, 4.5)
c1 = p.c('m1', 'w', 'separated'); c2 = p.c('w', 'm2', 'separated'); c3 = p.c('w', 'm3')
p.p('a', 'M', 1, 0.5); p.p('b', 'F', 1, 1.5)
p.p('c', 'F', 1, 2.5); p.p('d', 'M', 1, 3.5)
p.p('e', 'M', 1, 4.5)
p.k(c1, ['a', 'b']); p.k(c2, ['c', 'd']); p.k(c3, ['e'])

# 06 first cousins marry
p = ped('06-first-cousins', 'First cousins with children (consanguineous loop)')
p.p('gf', 'M', 0, 2); p.p('gm', 'F', 0, 3); c0 = p.c('gf', 'gm')
p.p('w1', 'F', 1, 0); p.p('b1', 'M', 1, 1); p.p('s2', 'F', 1, 4); p.p('h2', 'M', 1, 5)
p.k(c0, ['b1', 's2'])
c1 = p.c('b1', 'w1'); c2 = p.c('h2', 's2')
p.p('x1', 'F', 2, 0.5); p.p('cou1', 'M', 2, 1.5); p.p('cou2', 'F', 2, 3.5); p.p('x2', 'M', 2, 4.5)
p.k(c1, ['x1', 'cou1']); p.k(c2, ['cou2', 'x2'])
c3 = p.c('cou1', 'cou2', 'consanguineous')
p.p('aff', 'M', 3, 2, 'affected', affected=True, proband=True); p.p('sib', 'F', 3, 3)
p.k(c3, ['aff', 'sib'])

# 07 double first cousins and a marriage between their children
p = ped('07-double-cousins', 'Two brothers marry two sisters; two of their children marry')
p.p('a_gf', 'M', 0, 0); p.p('a_gm', 'F', 0, 1); ca = p.c('a_gf', 'a_gm')
p.p('b_gf', 'M', 0, 4); p.p('b_gm', 'F', 0, 5); cb = p.c('b_gf', 'b_gm')
p.p('br1', 'M', 1, 0); p.p('br2', 'M', 1, 2); p.p('si1', 'F', 1, 1); p.p('si2', 'F', 1, 3)
p.k(ca, ['br1', 'br2']); p.k(cb, ['si1', 'si2'])
c1 = p.c('br1', 'si1'); c2 = p.c('br2', 'si2')
p.p('k1', 'M', 2, 0); p.p('k2', 'F', 2, 1); p.p('k3', 'M', 2, 2); p.p('k4', 'F', 2, 3)
p.k(c1, ['k1', 'k2']); p.k(c2, ['k3', 'k4'])
c3 = p.c('k1', 'k4', 'consanguineous')
p.p('z', 'F', 3, 1.5, proband=True, affected=True)
p.k(c3, ['z'])

# 08 uncle marries niece (spans generations)
p = ped('08-uncle-niece', 'An uncle and his niece have children (partners from different generations)')
p.p('gf', 'M', 0, 1); p.p('gm', 'F', 0, 2); c0 = p.c('gf', 'gm')
p.p('bro', 'M', 1, 0); p.p('bw', 'F', 1, 1); p.p('unc', 'M', 1, 3, 'uncle')
p.k(c0, ['bro', 'unc'])
c1 = p.c('bro', 'bw')
p.p('n1', 'M', 2, 0); p.p('niece', 'F', 2, 1.5, 'niece')
p.k(c1, ['n1', 'niece'])
c2 = p.c('unc', 'niece', 'consanguineous')
p.p('ch1', 'M', 3, 2, proband=True, affected=True); p.p('ch2', 'F', 3, 3)
p.k(c2, ['ch1', 'ch2'])

# 09 sororate: a man marries his late wife's sister
p = ped('09-sororate', "A man has children with two sisters, one after the other")
p.p('gf', 'M', 0, 2); p.p('gm', 'F', 0, 3); c0 = p.c('gf', 'gm')
p.p('man', 'M', 1, 0, 'husband'); p.p('sis1', 'F', 1, 1, 'd. 30', deceased=True); p.p('sis2', 'F', 1, 3); p.p('sis3', 'F', 1, 4)
p.k(c0, ['sis1', 'sis2', 'sis3'])
c1 = p.c('man', 'sis1'); c2 = p.c('man', 'sis2')
p.p('a', 'M', 2, 0); p.p('b', 'F', 2, 1)
p.p('c', 'M', 2, 2.5); p.p('d', 'F', 2, 3.5)
p.k(c1, ['a', 'b']); p.k(c2, ['c', 'd'])

# 10 levirate: a woman marries her late husband's brother
p = ped('10-levirate', "A woman has children with two brothers")
p.p('gf', 'M', 0, 1); p.p('gm', 'F', 0, 2); c0 = p.c('gf', 'gm')
p.p('b1', 'M', 1, 0, 'd. 40', deceased=True); p.p('wid', 'F', 1, 1.5, 'widow'); p.p('b2', 'M', 1, 3)
p.k(c0, ['b1', 'b2'])
c1 = p.c('b1', 'wid'); c2 = p.c('b2', 'wid')
p.p('a', 'F', 2, 0); p.p('b', 'M', 2, 1)
p.p('c', 'F', 2, 2.5)
p.k(c1, ['a', 'b']); p.k(c2, ['c'])

# 11 second cousins marry (three-generation loop)
p = ped('11-second-cousins', 'Second cousins marry: their grandfathers were brothers')
p.p('ggf', 'M', 0, 2.5); p.p('ggm', 'F', 0, 3.5); c0 = p.c('ggf', 'ggm')
p.p('j', 'M', 1, 1, 'John'); p.p('jw', 'F', 1, 0); p.p('ar', 'M', 1, 5, 'Arthur'); p.p('aw', 'F', 1, 6)
p.k(c0, ['j', 'ar'])
c1 = p.c('jw', 'j'); c2 = p.c('ar', 'aw')
p.p('mi', 'M', 2, 1, 'Michael'); p.p('an', 'F', 2, 2); p.p('ph', 'M', 2, 5); p.p('ru', 'F', 2, 6)
p.k(c1, ['mi']); p.k(c2, ['ph'])
c3 = p.c('mi', 'an'); c4 = p.c('ph', 'ru')
p.p('li', 'F', 3, 2.5, 'Lisa'); p.p('da', 'M', 3, 4.5, 'David', proband=True); p.p('am', 'F', 3, 6, 'Amelia', affected=True)
p.k(c3, ['li']); p.k(c4, ['da', 'am'])
c5 = p.c('li', 'da', 'consanguineous')
p.p('pr', 'U', 4, 3.5, centre='P')
p.k(c5, ['pr'])

# 12 twins and triplets
p = ped('12-twins', 'Identical and non-identical twins in one sibship')
p.p('f', 'M', 0, 1.5); p.p('m', 'F', 0, 2.5); c = p.c('f', 'm')
for i, s in enumerate('MMFFMF'):
    p.p('k%d' % i, s, 1, i)
p.k(c, ['k%d' % i for i in range(6)])
p.t('k0', 'k1', 'identical'); p.t('k3', 'k4', 'nonidentical')

# 13 adoption, no children and infertility
p = ped('13-adoption-lines', 'Adopted in (dashed), no-children and infertility bars')
p.p('f', 'M', 0, 0); p.p('m', 'F', 0, 1); c = p.c('f', 'm')
p.p('a', 'F', 1, -0.5, adopted=True); p.p('b', 'M', 1, 0.5); p.p('cc', 'F', 1, 1.5)
p.k(c, ['a', 'b', 'cc'], dashed=['a'])
p.p('bw', 'F', 1, 2.5); c2 = p.c('b', 'bw')
p.p('nol', 'U', 2, 1.5, line='no-offspring')
p.k(c2, ['nol'])
p.p('ch', 'M', 1, 3.5); c3 = p.c('ch', 'cc')
p.p('inf', 'U', 2, 2.5, line='infertile')
p.k(c3, ['inf'])

# 14 three separate families
p = ped('14-separate', 'Three unconnected families and a single person')
for fam in range(3):
    b = fam * 4
    p.p('f%d' % fam, 'M', 0, b); p.p('m%d' % fam, 'F', 0, b + 1)
    cc = p.c('f%d' % fam, 'm%d' % fam)
    ks = []
    for j in range(fam + 1):
        kid = 'k%d_%d' % (fam, j)
        p.p(kid, 'MF'[j % 2], 1, b + j)
        ks.append(kid)
    p.k(cc, ks)
p.p('alone', 'F', 0, 13)

# 15 a realistic four-generation family with several joins
p = ped('15-realistic', 'Four generations: both sides of the family, spouses with their own parents, cousins')
# generation 0: four founder couples
p.p('A1', 'M', 0, 0, 'd. 80', deceased=True); p.p('A2', 'F', 0, 1, 'd. 85', deceased=True); ca = p.c('A1', 'A2')
p.p('B1', 'M', 0, 4); p.p('B2', 'F', 0, 5, 'breast ca dx 60', affected=True); cb = p.c('B1', 'B2')
p.p('C1', 'M', 0, 9); p.p('C2', 'F', 0, 10); cc_ = p.c('C1', 'C2')
p.p('D1', 'M', 0, 13); p.p('D2', 'F', 0, 14); cd = p.c('D1', 'D2')
# generation 1
p.p('a1', 'M', 1, -1); p.p('a1w', 'F', 1, 0); p.p('a2', 'M', 1, 1.5, 'grandfather, 78'); p.p('a3', 'F', 1, 3)
p.k(ca, ['a1', 'a2', 'a3'])
p.p('b1', 'F', 1, 2.5, 'grandmother, 75', affected=True); p.p('b2', 'M', 1, 5); p.p('b3', 'F', 1, 6)
p.k(cb, ['b1', 'b2', 'b3'])
p.p('c1', 'M', 1, 8); p.p('c2', 'M', 1, 9.5, 'grandfather, 80'); p.p('c3', 'F', 1, 11)
p.k(cc_, ['c1', 'c2', 'c3'])
p.p('d1', 'F', 1, 10.5, 'grandmother, 79'); p.p('d2', 'M', 1, 13)
p.k(cd, ['d1', 'd2'])
g1a = p.c('a1', 'a1w'); g1b = p.c('a2', 'b1'); g1c = p.c('c2', 'd1')
# generation 2
p.p('cous1', 'F', 2, -1); p.p('cous2', 'M', 2, 0)
p.k(g1a, ['cous1', 'cous2'])
p.p('u1', 'M', 2, 1, 'uncle'); p.p('dad', 'M', 2, 2.5, 'Dad, 52'); p.p('au1', 'F', 2, 3.5, 'ovarian ca', affected=True)
p.k(g1b, ['u1', 'dad', 'au1'])
p.p('mum', 'F', 2, 7, 'Mum, 50'); p.p('mu', 'M', 2, 8)
p.k(g1c, ['mum', 'mu'])
g2 = p.c('dad', 'mum')
p.p('muw', 'F', 2, 9); g2b = p.c('mu', 'muw')
# generation 3
p.p('sib1', 'M', 3, 3.5); p.p('pro', 'F', 3, 4.5, 'proband, 25', proband=True, affected=True); p.p('sib2', 'F', 3, 5.5)
p.k(g2, ['sib1', 'pro', 'sib2'])
p.p('mc1', 'M', 3, 7.5); p.p('mc2', 'F', 3, 8.5)
p.k(g2b, ['mc1', 'mc2'])

# 16 remarriage chain
p = ped('16-remarriage-chain', 'A chain of partnerships: A-B, B-C, C-D, each with children')
p.p('A', 'F', 0, 0); p.p('B', 'M', 0, 1); p.p('C', 'F', 0, 2); p.p('D', 'M', 0, 3)
c1 = p.c('B', 'A', 'separated'); c2 = p.c('B', 'C', 'separated'); c3 = p.c('D', 'C')
p.p('x1', 'M', 1, 0.5); p.p('x2', 'F', 1, 1.5); p.p('x3', 'F', 1, 2.5); p.p('x4', 'M', 1, 3.5)
p.k(c1, ['x1']); p.k(c2, ['x2', 'x3']); p.k(c3, ['x4'])

# 17 a widow marries her late husband's son (step-relationship across generations)
p = ped('17-stepson', "A widow later has a child with her late husband's son from his first marriage")
p.p('h', 'M', 0, 1, 'd. 70', deceased=True); p.p('w1', 'F', 0, 0, 'first wife'); p.p('w2', 'F', 0, 2.5, 'second wife')
c1 = p.c('w1', 'h', 'separated'); c2 = p.c('h', 'w2')
p.p('son', 'M', 1, 0.5, 'son'); p.p('dau', 'F', 1, 1.5)
p.k(c1, ['son', 'dau'])
p.p('hs', 'F', 1, 3)
p.k(c2, ['hs'])
c3 = p.c('son', 'w2')
p.p('kid', 'M', 2, 1.5, proband=True)
p.k(c3, ['kid'])

# 18 three joined families
p = ped('18-three-families', 'A couple whose parents are both drawn, and whose child marries into a third drawn family')
p.p('a1', 'M', 0, 0); p.p('a2', 'F', 0, 1); ca = p.c('a1', 'a2')
p.p('b1', 'M', 0, 3); p.p('b2', 'F', 0, 4); cb = p.c('b1', 'b2')
p.p('x', 'M', 1, 1, 'Xavier'); p.p('xs', 'F', 1, 0)
p.k(ca, ['xs', 'x'])
p.p('y', 'F', 1, 3, 'Yvonne'); p.p('yb', 'M', 1, 4)
p.k(cb, ['y', 'yb'])
cxy = p.c('x', 'y')
p.p('c1', 'M', 0, 7); p.p('c2', 'F', 0, 8); cc_ = p.c('c1', 'c2')
p.p('z', 'F', 1, 7.5)
p.k(cc_, ['z'])
p.p('zh', 'M', 1, 6.5); czz = p.c('zh', 'z')
p.p('k1', 'M', 2, 1.5); p.p('k2', 'F', 2, 2.5, 'Kate')
p.k(cxy, ['k1', 'k2'])
p.p('w', 'M', 2, 4.5, 'Will')
p.k(czz, ['w'])
ckw = p.c('w', 'k2')
p.p('gk', 'F', 3, 3.5, proband=True)
p.k(ckw, ['gk'])

# 19 free-position (pinned) people
p = ped('19-pins', 'A family where two people are pinned (free position)')
p.p('f', 'M', 0, 0); p.p('m', 'F', 0, 1); c = p.c('f', 'm')
for i in range(5):
    p.p('k%d' % i, 'MF'[i % 2], 1, -1.5 + i, pin=(i == 2))
p.k(c, ['k%d' % i for i in range(5)])
p.p('k0w', 'F', 1, 4); c2 = p.c('k0', 'k0w')
p.p('g', 'M', 2, 2, pin=True)
p.k(c2, ['g'])

# 20 singletons and a lone couple
p = ped('20-singletons', 'People with no relationships, and a couple with no children')
for i in range(4):
    p.p('s%d' % i, 'MFU'[i % 3], 0, i * 1.0)
p.p('cp1', 'M', 1, 0); p.p('cp2', 'F', 1, 1); p.c('cp1', 'cp2')

# 21 a deep descendant tree
p = ped('21-descendants', 'Five generations of descendants from one couple')
rnd = random.Random(21)
p.p('r1', 'M', 0, 6); p.p('r2', 'F', 0, 7)
front = [(p.c('r1', 'r2'), 6.5)]
cnt = 0
for gen in range(1, 5):
    nxt = []
    for cid, cx in front:
        nk = rnd.randint(2, 4) if gen < 4 else rnd.randint(1, 4)
        ks = []
        for j in range(nk):
            cnt += 1
            kid = 'd%d' % cnt
            p.p(kid, 'MF'[rnd.randint(0, 1)], gen, cx + (j - nk / 2) * 1.1)
            ks.append(kid)
            if gen < 4 and (rnd.random() < 0.55 or j == 0):
                cnt += 1
                sp = 'd%d' % cnt
                sx = p.people[kid]['sex']
                p.p(sp, 'F' if sx == 'M' else 'M', gen, cx + (j - nk / 2) * 1.1 + 0.6)
                nxt.append((p.c(kid, sp) if sx == 'M' else p.c(sp, kid), cx + (j - nk / 2) * 1.1))
        p.k(cid, ks)
    front = nxt

# 22 multiple loops: child of a cousin marriage marries a cousin again
p = ped('22-repeated-consanguinity', 'Two generations of cousin marriages in one family')
p.p('g1', 'M', 0, 2); p.p('g2', 'F', 0, 3); c0 = p.c('g1', 'g2')
p.p('a', 'M', 1, 0); p.p('aw', 'F', 1, 1); p.p('b', 'F', 1, 4); p.p('bh', 'M', 1, 5); p.p('c', 'M', 1, 6.5); p.p('cw', 'F', 1, 7.5)
p.k(c0, ['a', 'b', 'c'])
ca = p.c('a', 'aw'); cb = p.c('bh', 'b'); cc_ = p.c('c', 'cw')
p.p('a1', 'M', 2, 0.5); p.p('b1', 'F', 2, 4.5); p.p('b2', 'M', 2, 5.5); p.p('c1', 'F', 2, 7)
p.k(ca, ['a1']); p.k(cb, ['b1', 'b2']); p.k(cc_, ['c1'])
x1 = p.c('a1', 'b1', 'consanguineous'); x2 = p.c('b2', 'c1', 'consanguineous')
p.p('q1', 'M', 3, 2); p.p('q2', 'F', 3, 6)
p.k(x1, ['q1']); p.k(x2, ['q2'])
x3 = p.c('q1', 'q2', 'consanguineous')
p.p('z', 'M', 4, 4, proband=True, affected=True)
p.k(x3, ['z'])

# 23 a sibship where three siblings marry people whose parents are drawn
p = ped('23-many-joins', 'Three siblings married to people whose own parents are drawn')
p.p('g1', 'M', 0, 6); p.p('g2', 'F', 0, 7); c0 = p.c('g1', 'g2')
sibs = []
for i in range(5):
    sid = 's%d' % i
    p.p(sid, 'MF'[i % 2], 1, 3 + i * 2)
    sibs.append(sid)
p.k(c0, sibs)
for i in (0, 2, 4):
    sid = 's%d' % i
    base = -2 + i * 5
    p.p('ip%d_1' % i, 'M', 0, base); p.p('ip%d_2' % i, 'F', 0, base + 1)
    ci = p.c('ip%d_1' % i, 'ip%d_2' % i)
    sp = 'sp%d' % i
    p.p(sp, 'F' if p.people[sid]['sex'] == 'M' else 'M', 1, 3 + i * 2 + 1)
    p.p('spsib%d' % i, 'M', 1, base)
    p.k(ci, [sp, 'spsib%d' % i])
    cc_ = p.c(sid, sp) if p.people[sid]['sex'] == 'M' else p.c(sp, sid)
    p.p('kid%d' % i, 'F', 2, 3 + i * 2 + 0.5)
    p.k(cc_, ['kid%d' % i])

# 24 four sets of half-siblings
p = ped('24-four-way-halfsibs', 'Two people each with two partners, linked: W1-M2-W-M1 with children of each couple')
p.p('w1', 'F', 0, 0); p.p('m2', 'M', 0, 1); p.p('w', 'F', 0, 2.5, 'Wendy'); p.p('m1', 'M', 0, 4)
c1 = p.c('m2', 'w1', 'separated'); c2 = p.c('m2', 'w'); c3 = p.c('m1', 'w', 'separated')
p.p('a', 'M', 1, 0); p.p('b', 'F', 1, 1.5); p.p('cc', 'M', 1, 2.5); p.p('d', 'F', 1, 3.5); p.p('e', 'M', 1, 4.5)
p.k(c1, ['a']); p.k(c2, ['b', 'cc']); p.k(c3, ['d', 'e'])

# 25 an impossible structure: a father and daughter have a child
p = ped('25-cycle', 'A father and his daughter have a child (cannot share a row)')
p.p('f', 'M', 0, 0); p.p('m', 'F', 0, 1); c0 = p.c('f', 'm')
p.p('d', 'F', 1, 1)
p.k(c0, ['d'])
c1 = p.c('f', 'd', 'consanguineous')
p.p('k', 'M', 2, 0.5, affected=True)
p.k(c1, ['k'])

# 26 long notes under every symbol
p = ped('26-long-notes', 'Every person has long notes under their symbol')
p.p('f', 'M', 0, 1, 'Robert Smith, 72\nbowel cancer dx 58\nMLH1 c.1852_1854del'); p.p('m', 'F', 0, 2, 'Margaret, 70\nendometrial ca dx 52'); c = p.c('f', 'm')
for i in range(5):
    p.p('k%d' % i, 'MF'[i % 2], 1, i * 0.8, 'child %d, %d\npolyps at 3%d\ncolonoscopy every 2 yrs' % (i + 1, 45 - i, i))
p.k(c, ['k%d' % i for i in range(5)])
p.p('k1h', 'M', 1, 4.5, 'husband'); c2 = p.c('k1h', 'k1')
p.p('gc', 'F', 2, 2, 'granddaughter, 20\npredictive test: positive')
p.k(c2, ['gc'])

# 27 a person who appears with partners on both sides and both have parents
p = ped('27-two-inlaws', 'A man married twice, both wives with their parents drawn')
p.p('mp1', 'M', 0, 1); p.p('mp2', 'F', 0, 2); c0 = p.c('mp1', 'mp2')
p.p('man', 'M', 1, 1.5, 'Peter')
p.k(c0, ['man'])
p.p('w1p1', 'M', 0, -2); p.p('w1p2', 'F', 0, -1); c1 = p.c('w1p1', 'w1p2')
p.p('w1', 'F', 1, 0); p.p('w1s', 'M', 1, -1.5)
p.k(c1, ['w1s', 'w1'])
p.p('w2p1', 'M', 0, 4); p.p('w2p2', 'F', 0, 5); c2 = p.c('w2p1', 'w2p2')
p.p('w2', 'F', 1, 3); p.p('w2s', 'F', 1, 4.5)
p.k(c2, ['w2', 'w2s'])
cm1 = p.c('w1', 'man', 'separated'); cm2 = p.c('man', 'w2')
p.p('k1', 'M', 2, 0.5); p.p('k2', 'F', 2, 2.5); p.p('k3', 'M', 2, 3.5)
p.k(cm1, ['k1']); p.k(cm2, ['k2', 'k3'])

# 28 miscarriages and pregnancies mixed in a sibship
p = ped('28-losses', 'A sibship with losses, a pregnancy and a stillbirth in birth order')
p.p('f', 'M', 0, 2); p.p('m', 'F', 0, 3); c = p.c('f', 'm')
spec = [('k0', 'F', {}), ('l1', 'U', {'loss': True}), ('k1', 'M', {}), ('l2', 'U', {'loss': True}), ('l3', 'U', {'loss': True}), ('k2', 'M', {'deceased': True}), ('pg', 'U', {'centre': 'P'})]
for i, (pid, s, f) in enumerate(spec):
    p.p(pid, s, 1, i * 0.8, **f)
p.k(c, [s[0] for s in spec])

# 29 a large pedigree (about 170 people): four founder families that marry
# into each other over five generations
p = ped('29-large', 'About 170 people over six generations, with marriages between the founder families')
rnd = random.Random(29)
cnt = [0]
def nid(pref):
    cnt[0] += 1
    return '%s%d' % (pref, cnt[0])
gen_people = {0: []}
couples_by_gen = {0: []}
for f in range(4):
    a = p.p(nid('F'), 'M', 0, f * 6); b = p.p(nid('F'), 'F', 0, f * 6 + 1)
    couples_by_gen[0].append((p.c(a, b), f * 6 + 0.5, f))
for gen in range(1, 6):
    kids_this = []
    for cid, cx, fam in couples_by_gen[gen - 1]:
        nk = rnd.randint(2, 6) if gen < 4 else rnd.randint(0, 3)
        ks = []
        for j in range(nk):
            k = p.p(nid('k'), 'MF'[rnd.randint(0, 1)], gen, cx + (j - nk / 2) * 1.1, 'person %d' % cnt[0] if rnd.random() < 0.3 else '')
            ks.append(k); kids_this.append((k, fam))
        if ks:
            p.k(cid, ks)
    couples_by_gen[gen] = []
    if gen == 5:
        break
    rnd.shuffle(kids_this)
    used = set()
    for i, (k, fam) in enumerate(kids_this):
        if k in used or rnd.random() > 0.55:
            continue
        sx = p.people[k]['sex']
        partner = None
        # sometimes marry someone from another founder family
        if rnd.random() < 0.25:
            for k2, fam2 in kids_this:
                if k2 not in used and k2 != k and fam2 != fam and p.people[k2]['sex'] != sx:
                    partner = k2; break
        if partner is None:
            partner = p.p(nid('s'), 'F' if sx == 'M' else 'M', gen, p.people[k]['x'] + 0.6)
        used.add(k); used.add(partner)
        a, b = (k, partner) if sx == 'M' else (partner, k)
        if len(p.people) > 150 and gen >= 3:
            continue
        couples_by_gen[gen].append((p.c(a, b), p.people[k]['x'] + 0.3, fam))

# 30 twenty siblings
p = ped('30-twenty-sibs', 'Twenty siblings, about half married, with grandparents on both sides')
p.p('pgf', 'M', 0, 4); p.p('pgm', 'F', 0, 5); cp = p.c('pgf', 'pgm')
p.p('mgf', 'M', 0, 16); p.p('mgm', 'F', 0, 17); cm = p.c('mgf', 'mgm')
p.p('dad', 'M', 1, 9, 'father, 70'); p.p('mum', 'F', 1, 10, 'mother, 68')
p.p('dsib', 'F', 1, 3); p.p('msib', 'M', 1, 18)
p.k(cp, ['dsib', 'dad']); p.k(cm, ['mum', 'msib'])
cpar = p.c('dad', 'mum')
rnd = random.Random(30)
sibs = []
x = -2
for i in range(20):
    sid = 'c%d' % i
    p.p(sid, 'MF'[rnd.randint(0, 1)], 2, x, 'child %d' % (i + 1), proband=(i == 7), affected=(i in (3, 7, 12)))
    sibs.append(sid)
    x += 1.2
    if rnd.random() < 0.5:
        sp = 'sp%d' % i
        p.p(sp, 'F' if p.people[sid]['sex'] == 'M' else 'M', 2, x)
        x += 1.2
        cc = p.c(sid, sp)
        nk = rnd.randint(0, 3)
        gk = ['g%d_%d' % (i, j) for j in range(nk)]
        for j, g in enumerate(gk):
            p.p(g, 'MF'[j % 2], 3, x - 1.8 + j)
        if gk:
            p.k(cc, gk)
p.k(cpar, sibs)

# 31 a man and his grand-niece have a child (partners two generations apart)
p = ped('31-grand-niece', 'A man and his grand-niece have a child: partners two generations apart')
p.p('gf', 'M', 0, 1); p.p('gm', 'F', 0, 2); c0 = p.c('gf', 'gm')
p.p('bro', 'M', 1, 0); p.p('bw', 'F', 1, 1); p.p('man', 'M', 1, 4, 'great-uncle')
p.k(c0, ['bro', 'man'])
c1 = p.c('bro', 'bw')
p.p('nep', 'M', 2, 0.5); p.p('nw', 'F', 2, 1.5)
p.k(c1, ['nep'])
c2 = p.c('nep', 'nw')
p.p('gn', 'F', 3, 1, 'grand-niece'); p.p('gn2', 'M', 3, 2)
p.k(c2, ['gn', 'gn2'])
c3 = p.c('man', 'gn', 'consanguineous')
p.p('kid', 'M', 4, 2.5, proband=True, affected=True)
p.k(c3, ['kid'])

# 32 two people with several partners each, one partnership between them
p = ped('32-two-hubs', 'Ann has three partners; one of them, Ben, has two other partners')
p.p('p1', 'M', 0, 0); p.p('ann', 'F', 0, 1, 'Ann'); p.p('p2', 'M', 0, 2); p.p('ben', 'M', 0, 3.5, 'Ben'); p.p('q1', 'F', 0, 5); p.p('q2', 'F', 0, 6.5)
ca1 = p.c('p1', 'ann'); ca2 = p.c('ann', 'p2', 'separated'); cab = p.c('ben', 'ann'); cb1 = p.c('ben', 'q1', 'separated'); cb2 = p.c('ben', 'q2')
p.p('a1', 'M', 1, 0); p.p('a2', 'F', 1, 1.5); p.p('ab1', 'F', 1, 2.5); p.p('ab2', 'M', 1, 3.5); p.p('b1', 'M', 1, 5); p.p('b2', 'F', 1, 6.5)
p.k(ca1, ['a1']); p.k(ca2, ['a2']); p.k(cab, ['ab1', 'ab2']); p.k(cb1, ['b1']); p.k(cb2, ['b2'])

# 33 his, hers and theirs, with the former partners' new families
p = ped('33-his-hers-theirs', 'A couple who both have children from earlier partners, whose former partners have new families')
p.p('mp1', 'M', 0, 3); p.p('mp2', 'F', 0, 4); cmp_ = p.c('mp1', 'mp2')
p.p('wp1', 'M', 0, 8); p.p('wp2', 'F', 0, 9); cwp = p.c('wp1', 'wp2')
p.p('e1h', 'M', 1, 0); p.p('e1', 'F', 1, 1.5, 'first wife'); p.p('m', 'M', 1, 3.5, 'Mark'); p.p('w', 'F', 1, 5.5, 'Wendy'); p.p('e2', 'M', 1, 7.5, 'first husband'); p.p('e2w', 'F', 1, 9)
p.k(cmp_, ['m']); p.k(cwp, ['w'])
c1 = p.c('m', 'e1', 'separated'); c2 = p.c('m', 'w'); c3 = p.c('e2', 'w', 'separated'); c4 = p.c('e1h', 'e1'); c5 = p.c('e2', 'e2w')
p.p('k1', 'M', 2, 2); p.p('k2', 'F', 2, 3); p.p('k4', 'F', 2, 4.5, proband=True); p.p('k5', 'M', 2, 5.5); p.p('k3', 'M', 2, 7); p.p('k6', 'F', 2, 0.5); p.p('k7', 'M', 2, 9)
p.k(c1, ['k1', 'k2']); p.k(c2, ['k4', 'k5']); p.k(c3, ['k3']); p.k(c4, ['k6']); p.k(c5, ['k7'])

# 35 twins who marry, and triplets
p = ped('35-twins-married', 'Identical twins who both marry and have children; triplets in the next generation')
p.p('f', 'M', 0, 2); p.p('m', 'F', 0, 3); c0 = p.c('f', 'm')
p.p('t1', 'F', 1, 1); p.p('t2', 'F', 1, 3); p.p('s', 'M', 1, 5)
p.k(c0, ['t1', 't2', 's']); p.t('t1', 't2', 'identical')
p.p('h1', 'M', 1, 0); p.p('h2', 'M', 1, 4)
c1 = p.c('h1', 't1'); c2 = p.c('h2', 't2')
p.p('x1', 'M', 2, -0.5); p.p('x2', 'F', 2, 0.5); p.p('x3', 'M', 2, 1.5)
p.k(c1, ['x1', 'x2', 'x3']); p.t('x1', 'x2', 'nonidentical'); p.t('x2', 'x3', 'nonidentical')
p.p('y1', 'F', 2, 3.5); p.p('y2', 'M', 2, 4.5)
p.k(c2, ['y1', 'y2'])

# 37 consanguinity across generations: first cousins once removed
p = ped('37-cousins-removed', 'First cousins once removed have a child (partners from different generations)')
p.p('gf', 'M', 0, 2); p.p('gm', 'F', 0, 3); c0 = p.c('gf', 'gm')
p.p('s1', 'M', 1, 0); p.p('s1w', 'F', 1, 1); p.p('s2', 'F', 1, 4); p.p('s2h', 'M', 1, 5)
p.k(c0, ['s1', 's2'])
c1 = p.c('s1', 's1w'); c2 = p.c('s2h', 's2')
p.p('a', 'M', 2, 0.5, 'Adam'); p.p('cz', 'F', 2, 4.5); p.p('czh', 'M', 2, 5.5)
p.k(c1, ['a']); p.k(c2, ['cz'])
c3 = p.c('cz', 'czh')
p.p('b', 'F', 3, 4, 'Beth')
p.k(c3, ['b'])
c4 = p.c('a', 'b', 'consanguineous')
p.p('kid', 'U', 4, 2, centre='P')
p.k(c4, ['kid'])

# 38 an ancestor chart: the proband's ancestors for four generations
p = ped('38-ancestors', "Four generations of the proband's ancestors, with some of their siblings")
rnd = random.Random(38)
p.p('pro', 'F', 4, 7.5, 'proband', proband=True)
p.p('bro', 'M', 4, 8.5)
frontier = [('pro', 7.5, 3)]
level = 3
cntA = [0]
def anc(child, x, gen, width):
    if gen < 0:
        return None
    cntA[0] += 1
    f = p.p('af%d' % cntA[0], 'M', gen, x - width / 2)
    m = p.p('am%d' % cntA[0], 'F', gen, x + width / 2)
    c = p.c(f, m)
    return c, f, m
def build(child, x, gen, width, kids_extra):
    if gen < 0:
        return
    res = anc(child, x, gen, width)
    c, f, m = res
    ks = [child] + kids_extra
    p.k(c, ks)
    if gen - 1 >= 0 and rnd.random() < 0.85:
        sib = p.p('as%d' % cntA[0], 'MF'[rnd.randint(0, 1)], gen, x - width / 2 - 1)
        build(f, x - width / 2, gen - 1, width / 2, [sib])
    if gen - 1 >= 0 and rnd.random() < 0.85:
        sib = p.p('at%d' % cntA[0], 'MF'[rnd.randint(0, 1)], gen, x + width / 2 + 1)
        build(m, x + width / 2, gen - 1, width / 2, [sib])
build('pro', 8, 3, 8, ['bro'])

# 39 many unconnected families
p = ped('39-many-families', 'Five unconnected families of different sizes and three single people')
rnd = random.Random(39)
xb = 0
for fi in range(5):
    g0 = 'f%d_a' % fi; g1 = 'f%d_b' % fi
    p.p(g0, 'M', 0, xb); p.p(g1, 'F', 0, xb + 1)
    cc = p.c(g0, g1)
    nk = fi + 1
    ks = []
    for j in range(nk):
        k = p.p('f%d_k%d' % (fi, j), 'MF'[j % 2], 1, xb + j)
        ks.append(k)
    p.k(cc, ks)
    if fi >= 3:
        sp = p.p('f%d_sp' % fi, 'F' if p.people[ks[0]]['sex'] == 'M' else 'M', 1, xb + nk)
        c2 = p.c(ks[0], sp) if p.people[ks[0]]['sex'] == 'M' else p.c(sp, ks[0])
        g = p.p('f%d_g' % fi, 'F', 2, xb + 0.5)
        p.k(c2, [g])
    xb += nk + 3
for i in range(3):
    p.p('lone%d' % i, 'MFU'[i], i % 2, xb + i * 1.5)

# 40 free-position people inside a family
p = ped('40-mixed-pins', 'A pinned person in the middle of a sibship and a pinned spouse')
p.p('f', 'M', 0, 2); p.p('m', 'F', 0, 3); c = p.c('f', 'm')
for i in range(6):
    p.p('k%d' % i, 'MF'[i % 2], 1, i, pin=(i == 3))
p.k(c, ['k%d' % i for i in range(6)])
p.p('sp', 'F', 1, 6.2, pin=True); c2 = p.c('k4', 'sp')
p.p('g1', 'M', 2, 4.5); p.p('g2', 'F', 2, 5.5)
p.k(c2, ['g1', 'g2'])

# 41 a widow remarries; both husbands have their parents drawn
p = ped('41-remarriage-inlaws', "A widow's two husbands, both with their parents and siblings drawn")
p.p('h1f', 'M', 0, 0); p.p('h1m', 'F', 0, 1); c1 = p.c('h1f', 'h1m')
p.p('wf', 'M', 0, 3); p.p('wm', 'F', 0, 4); cw = p.c('wf', 'wm')
p.p('h2f', 'M', 0, 6); p.p('h2m', 'F', 0, 7); c2 = p.c('h2f', 'h2m')
p.p('h1s', 'F', 1, -0.5); p.p('h1', 'M', 1, 1, 'd. 45', deceased=True); p.p('w', 'F', 1, 3, 'widow'); p.p('wsib', 'M', 1, 4); p.p('h2', 'M', 1, 5.5); p.p('h2s', 'M', 1, 7)
p.k(c1, ['h1s', 'h1']); p.k(cw, ['w', 'wsib']); p.k(c2, ['h2', 'h2s'])
m1 = p.c('h1', 'w'); m2 = p.c('w', 'h2')
p.p('a', 'M', 2, 1); p.p('b', 'F', 2, 2); p.p('c_', 'F', 2, 5, proband=True)
p.k(m1, ['a', 'b']); p.k(m2, ['c_'])

# 42 a clinical pedigree with several lines of notes under everyone
p = ped('42-clinical-notes', 'A three-generation clinical pedigree with two to four lines of notes per person')
p.p('gf', 'M', 0, 1, 'John, d. 71\nprostate ca dx 66\nno testing'); p.p('gm', 'F', 0, 2.5, 'Mary, 90\nbreast ca dx 52\nBRCA2 c.5946del\n(tested 2019)'); c0 = p.c('gf', 'gm')
p.p('u', 'M', 1, -1, 'Peter, 64\nwell'); p.p('uw', 'F', 1, 0.5, 'Sue, 63\nwell'); p.p('d', 'M', 1, 2, 'David, 62\npancreatic ca dx 60\nBRCA2 +'); p.p('mo', 'F', 1, 3.5, 'Anne, 60\nwell\nnot tested'); p.p('a', 'F', 1, 5, 'Liz, 58\nbreast ca dx 45\novarian ca dx 55\nBRCA2 +', affected=True)
p.k(c0, ['u', 'd', 'a'])
cu = p.c('u', 'uw'); cd_ = p.c('d', 'mo')
p.p('c1', 'F', 2, -1, 'Kate, 35\nwell\nBRCA2 -'); p.p('c2', 'M', 2, 0.5, 'Tom, 33\nwell\nuntested')
p.p('pr', 'F', 2, 2, 'Emma, 32\nbreast ca dx 31\nBRCA2 +', proband=True, affected=True); p.p('sib', 'M', 2, 3.5, 'James, 29\nwell\nuntested')
p.k(cu, ['c1', 'c2']); p.k(cd_, ['pr', 'sib'])

# 43 a child with birth parents and adoptive parents both drawn
p = ped('43-two-sets-of-parents', 'An adopted child linked to her birth parents and (dashed) to her adoptive parents')
p.p('b1', 'M', 0, 0, 'birth father'); p.p('b2', 'F', 0, 1, 'birth mother'); cb = p.c('b1', 'b2', 'separated')
p.p('a1', 'M', 0, 4, 'adoptive father'); p.p('a2', 'F', 0, 5, 'adoptive mother'); ca = p.c('a1', 'a2')
p.p('sis', 'F', 1, 0); p.p('ad', 'F', 1, 2.5, 'adopted', adopted=True); p.p('bro', 'M', 1, 4.5)
p.k(cb, ['sis', 'ad']); p.k(ca, ['ad', 'bro'], dashed=['ad'])


def main():
    os.makedirs(OUT, exist_ok=True)
    names = []
    for p in S:
        for state in ('neat', 'messy', 'scramble'):
            if state == 'scramble' and p.name in ('14-separate', '20-singletons'):
                continue
            data = p.session(state, seed=sum(map(ord, p.name)))
            fn = '%s__%s.json' % (p.name, state)
            json.dump(data, open(os.path.join(OUT, fn), 'w'), indent=0)
            names.append(fn)
    # the practical's family files, as the Studio would load them
    pr = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'practical.json')
    if os.path.exists(pr):
        for nm, ses in sorted(json.load(open(pr)).items()):
            rnd = random.Random(sum(map(ord, nm)))
            for state in ('neat', 'messy', 'scramble'):
                d = json.loads(json.dumps(ses))
                for q in d['persons']:
                    if state == 'messy':
                        q['x'] = round(q['x'] + rnd.uniform(-60, 60), 1); q['y'] = round(q['y'] + rnd.uniform(-25, 25), 1)
                    elif state == 'scramble':
                        q['x'] = round(rnd.uniform(0, 1400), 1); q['y'] = round(rnd.uniform(0, 900), 1)
                d['_meta'] = dict(name='prac-' + nm, desc='practical: ' + nm, state=state)
                fn = 'prac-%s__%s.json' % (nm, state)
                json.dump(d, open(os.path.join(OUT, fn), 'w'), indent=0)
                names.append(fn)
    json.dump(names, open(os.path.join(OUT, 'index.json'), 'w'), indent=1)
    print(len(S), 'structures,', len(names), 'fixtures')


if __name__ == '__main__':
    main()
