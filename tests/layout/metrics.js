/* Layout measures for Pedigree Studio. Runs inside the page after a Tidy and
   reads the Studio's own globals (persons, partnerships, childLinks,
   twinLinks, SHAPE_SIZE).
     initial: Map id -> {x, y} of everyone before the Tidy (for sibling order
              and how far people moved)
   Set window.METRIC_DETAILS = [] first to get a list of what was counted.
   The score adds the problems up with rough weights: lower is better. */
window.LayoutMetrics = function (initial) {
  const S = SHAPE_SIZE, H = SHAPE_HALF;
  const P = new Map();
  persons.forEach((p, id) => {
    const x = parseFloat(p.el.style.left), y = parseFloat(p.el.style.top);
    const t = p.el.querySelector('.person-text');
    let tb = null, nb = null;
    if (t && (p.text || '').trim()) tb = { x1: x + t.offsetLeft, y1: y + t.offsetTop, x2: x + t.offsetLeft + t.offsetWidth, y2: y + t.offsetTop + t.offsetHeight };
    // the pedigree number, below the symbol
    const ne = p.el.querySelector('.person-number');
    if (ne && ne.textContent) nb = { x1: x + ne.offsetLeft, y1: y + ne.offsetTop, x2: x + ne.offsetLeft + ne.offsetWidth, y2: y + ne.offsetTop + ne.offsetHeight };
    P.set(id, { id, x, y, cx: x + H, cy: y + H, shape: p.shape, noSnap: !!p.noSnap, tb, nb, line: p.shape === 'no-offspring' || p.shape === 'infertile' });
  });
  const people = [...P.values()];
  const m = {};
  const box = (q, pad) => ({ x1: q.x - pad, y1: q.y - pad, x2: q.x + S + pad, y2: q.y + S + pad });
  const inter = (a, b) => a.x1 < b.x2 && b.x1 < a.x2 && a.y1 < b.y2 && b.y1 < a.y2;

  // 1. symbols overlapping (with a small margin)
  m.overlap = 0;
  for (let i = 0; i < people.length; i++) for (let j = i + 1; j < people.length; j++) {
    if (inter(box(people[i], 3), box(people[j], 3))) m.overlap++;
  }
  // 2. notes overlapping other notes or symbols
  m.textOverlap = 0;
  people.forEach((a) => {
    if (!a.tb) return;
    people.forEach((b) => {
      if (a === b) return;
      if (b.tb && a.id < b.id && inter(a.tb, b.tb)) m.textOverlap++;
      if (inter(a.tb, box(b, 0))) m.textOverlap++;
    });
  });
  // 3. pedigree numbers on notes (anyone's), symbols or other numbers
  m.numberOverlap = 0;
  people.forEach((a) => {
    if (!a.nb) return;
    people.forEach((b) => {
      if (b.tb && inter(a.nb, b.tb)) { m.numberOverlap++; if (window.METRIC_DETAILS) window.METRIC_DETAILS.push(['number-on-notes', a.id, b.id]); }
      if (inter(a.nb, box(b, 0))) { m.numberOverlap++; if (window.METRIC_DETAILS) window.METRIC_DETAILS.push(['number-on-symbol', a.id, b.id]); }
      if (b.nb && a.id < b.id && inter(a.nb, b.nb)) { m.numberOverlap++; if (window.METRIC_DETAILS) window.METRIC_DETAILS.push(['number-on-number', a.id, b.id]); }
    });
  });
  // partnerships
  m.partnerRowMismatch = 0; m.partnerBlocked = 0; m.partnerGapExcess = 0; m.partnerGapMax = 0;
  let pg = 0;
  partnerships.forEach((ps) => {
    const a = P.get(ps.fromId), b = P.get(ps.toId);
    if (!a || !b) return;
    if (Math.abs(a.y - b.y) > 2) m.partnerRowMismatch++;
    // a line drawn up and over the people in its way is not blocked
    const blockers = ps.routeSegs ? [] : people.filter((q) => q !== a && q !== b && segHitsBox(a.cx, a.cy, b.cx, b.cy, q, 4));
    if (blockers.length) m.partnerBlocked++;
    if (Math.abs(a.y - b.y) <= 2) {
      const ex = Math.max(0, Math.abs(a.x - b.x) - partnerGap) / partnerGap;
      m.partnerGapExcess += ex; m.partnerGapMax = Math.max(m.partnerGapMax, ex); pg++;
    }
  });
  if (pg) m.partnerGapExcess = +(m.partnerGapExcess / pg).toFixed(3);
  m.partnerGapMax = +m.partnerGapMax.toFixed(2);

  // families
  const fam = new Map();
  childLinks.forEach((cl) => {
    if (!fam.has(cl.partnershipId)) fam.set(cl.partnershipId, []);
    fam.get(cl.partnershipId).push(cl.childId);
  });
  m.childNotBelow = 0; m.dropOutside = 0; m.centreOffset = 0; m.sibshipIntruders = 0; m.siblingInversions = 0; m.misaligned = 0; m.rowSplit = 0;
  let nf = 0;
  fam.forEach((kids, pid) => {
    const ps = partnerships.find((q) => q.id === pid);
    if (!ps) return;
    const a = P.get(ps.fromId), b = P.get(ps.toId);
    const ks = kids.map((k) => P.get(k)).filter(Boolean);
    ks.forEach((k) => { if (k.y <= Math.max(a.y, b.y) + 10) m.childNotBelow++; });
    const mx = (a.cx + b.cx) / 2;
    const rowKids = ks.filter((k) => !k.noSnap);
    // siblings drawn in different generations
    if (rowKids.length > 1) {
      const cnt = new Map();
      rowKids.forEach((k) => { const y = Math.round(k.y / 5); cnt.set(y, (cnt.get(y) || 0) + 1); });
      const most = Math.max(...cnt.values());
      m.rowSplit += rowKids.length - most;
      if (rowKids.length - most && window.METRIC_DETAILS) window.METRIC_DETAILS.push(['rowSplit', pid, kids.join(',')]);
    }
    if (!rowKids.length) return;
    const lo = Math.min(...rowKids.map((k) => k.cx)), hi = Math.max(...rowKids.map((k) => k.cx));
    if (mx < lo - 2 || mx > hi + 2) m.dropOutside++;
    m.centreOffset += Math.abs(mx - (lo + hi) / 2); nf++;
    if (Math.abs(mx - (lo + hi) / 2) > 1.5) { m.misaligned++; if (window.METRIC_DETAILS) window.METRIC_DETAILS.push(['misaligned', pid, ps.fromId, ps.toId, 'drop', Math.round(mx * 10) / 10, 'kids', Math.round(lo * 10) / 10, Math.round(hi * 10) / 10, kids.join(',')]); }
    // people between the first and last child who are neither siblings nor their partners
    const kidSet = new Set(kids);
    const partnersOfKids = new Set();
    partnerships.forEach((q) => { if (kidSet.has(q.fromId)) partnersOfKids.add(q.toId); if (kidSet.has(q.toId)) partnersOfKids.add(q.fromId); });
    const rowY = new Set(rowKids.map((k) => Math.round(k.y)));
    people.forEach((q) => {
      if (kidSet.has(q.id) || partnersOfKids.has(q.id)) return;
      if (!rowY.has(Math.round(q.y))) return;
      if (q.cx > lo + 1 && q.cx < hi - 1) { m.sibshipIntruders++; if (window.METRIC_DETAILS) window.METRIC_DETAILS.push(['intruder', pid, q.id]); }
    });
    // birth order compared with the starting order
    if (initial) {
      const before = kids.slice().sort((u, v) => initial.get(u).x - initial.get(v).x);
      const after = kids.slice().sort((u, v) => P.get(u).x - P.get(v).x);
      const pos = new Map(after.map((k, i) => [k, i]));
      for (let i = 0; i < before.length; i++) for (let j = i + 1; j < before.length; j++) if (pos.get(before[i]) > pos.get(before[j])) m.siblingInversions++;
    }
  });
  if (nf) m.centreOffset = Math.round(m.centreOffset / nf);

  // drawn segments
  const segs = [];
  partnerships.forEach((ps) => {
    if (ps.routeSegs) {
      ps.routeSegs.forEach((s) => {
        if (s.type === 'h') segs.push({ x1: s.x1, y1: s.y, x2: s.x2, y2: s.y, fam: ps.id, kind: 'p', ends: [ps.fromId, ps.toId] });
        else segs.push({ x1: s.x, y1: s.y1, x2: s.x, y2: s.y2, fam: ps.id, kind: 'p', ends: [ps.fromId, ps.toId] });
      });
      return;
    }
    const x1 = +ps.el.getAttribute('x1'), y1 = +ps.el.getAttribute('y1'), x2 = +ps.el.getAttribute('x2'), y2 = +ps.el.getAttribute('y2');
    segs.push({ x1, y1, x2, y2, fam: ps.id, kind: 'p', ends: [ps.fromId, ps.toId] });
  });
  // read the plain line geometry (the drawn paths carry arcs where lines hop)
  childLinks.forEach((cl) => { try { updateChildLinkPos(cl); } catch (e) {} });
  childLinks.forEach((cl) => {
    const pts = (cl.els[0].getAttribute('d') || '').match(/-?[\d.]+(e-?\d+)?/g);
    if (!pts) return;
    const v = pts.map(Number);
    for (let i = 0; i + 3 < v.length; i += 2) {
      if (Math.abs(v[i] - v[i + 2]) < 0.01 && Math.abs(v[i + 1] - v[i + 3]) < 0.01) continue;
      segs.push({ x1: v[i], y1: v[i + 1], x2: v[i + 2], y2: v[i + 3], fam: cl.partnershipId, kind: 'c', ends: [cl.childId] });
    }
  });
  m.crossings = 0; m.collinear = 0;
  for (let i = 0; i < segs.length; i++) for (let j = i + 1; j < segs.length; j++) {
    const s = segs[i], t = segs[j];
    if (s.fam === t.fam) continue;
    // two partner lines from one person run along each other by design
    if (s.kind === 'p' && t.kind === 'p' && s.ends.some((e) => t.ends.includes(e))) continue;
    const r = segRel(s, t);
    if (r === 'cross') { m.crossings++; if (window.METRIC_DETAILS) window.METRIC_DETAILS.push(['cross', s.fam, s.ends.join(','), t.fam, t.ends.join(','), [s.x1, s.y1, s.x2, s.y2].map(Math.round).join(' '), [t.x1, t.y1, t.x2, t.y2].map(Math.round).join(' ')]); }
    else if (r === 'overlap') { m.collinear++; if (window.METRIC_DETAILS) window.METRIC_DETAILS.push(['collinear', s.fam, s.ends.join(','), t.fam, t.ends.join(',')]); }
  }
  // lines through symbols
  m.linesThroughSymbols = 0;
  segs.forEach((s) => {
    const fps = partnerships.find((q) => q.id === s.fam);
    const own = new Set([...(fps ? [fps.fromId, fps.toId] : []), ...s.ends]);
    people.forEach((q) => {
      if (own.has(q.id)) return;
      if (segHitsBox(s.x1, s.y1, s.x2, s.y2, q, -4)) { m.linesThroughSymbols++; if (window.METRIC_DETAILS) window.METRIC_DETAILS.push(['through', s.kind, s.fam, s.ends.join(','), q.id]); }
    });
  });
  // lines across pedigree numbers
  m.numberLines = 0;
  segs.forEach((s) => people.forEach((q) => {
    if (q.nb && segHitsRect(s.x1, s.y1, s.x2, s.y2, q.nb)) { m.numberLines++; if (window.METRIC_DETAILS) window.METRIC_DETAILS.push(['line-on-number', s.kind, s.fam, q.id]); }
  }));
  // twins side by side, and triplets and more together: only others born with them may sit between
  m.twinsApart = 0;
  twinLinks.forEach((t) => {
    const a = P.get(t.child1Id), b = P.get(t.child2Id);
    if (!a || !b) return;
    if (Math.abs(a.y - b.y) > 2) { m.twinsApart++; return; }
    const group = new Set(typeof twinGroup === 'function' ? twinGroup(t.child1Id, t.partnershipId) : [t.child1Id, t.child2Id]);
    const lo = Math.min(a.cx, b.cx), hi = Math.max(a.cx, b.cx);
    if (people.some((q) => !group.has(q.id) && Math.abs(q.y - a.y) < 2 && q.cx > lo && q.cx < hi)) m.twinsApart++;
  });
  // shape of the whole drawing
  const xs = people.map((q) => q.x), ys = people.map((q) => q.y);
  m.width = people.length ? Math.round(Math.max(...xs) - Math.min(...xs) + S) : 0;
  m.height = people.length ? Math.round(Math.max(...ys) - Math.min(...ys) + S) : 0;
  m.rows = new Set(people.filter((q) => !q.noSnap).map((q) => Math.round(q.y / 5))).size;
  if (initial) {
    let mv = 0, n = 0;
    people.forEach((q) => { const o = initial.get(q.id); if (o) { mv += Math.hypot(q.x - o.x, q.y - o.y); n++; } });
    m.meanMove = n ? Math.round(mv / n) : 0;
  }
  m.people = people.length;
  try { updateAllConnections(); } catch (e) {}
  m.score = Math.round(m.overlap * 100 + m.textOverlap * 15 + m.partnerRowMismatch * 30 + m.partnerBlocked * 30 + m.childNotBelow * 100 +
    m.crossings * 10 + m.collinear * 20 + m.linesThroughSymbols * 25 + m.sibshipIntruders * 10 + m.twinsApart * 20 +
    m.numberOverlap * 15 + m.numberLines * 15 +
    m.siblingInversions * 3 + m.dropOutside * 4 + m.partnerGapExcess * 20 + m.misaligned * 2 + m.rowSplit * 20);
  return m;

  function segHitsBox(x1, y1, x2, y2, q, pad) {
    return segHitsRect(x1, y1, x2, y2, { x1: q.x - pad, y1: q.y - pad, x2: q.x + S + pad, y2: q.y + S + pad });
  }
  function segHitsRect(x1, y1, x2, y2, b) {
    // Liang-Barsky clip
    let t0 = 0, t1 = 1;
    const dx = x2 - x1, dy = y2 - y1;
    const p = [-dx, dx, -dy, dy], qq = [x1 - b.x1, b.x2 - x1, y1 - b.y1, b.y2 - y1];
    for (let i = 0; i < 4; i++) {
      if (Math.abs(p[i]) < 1e-9) { if (qq[i] < 0) return false; }
      else {
        const r = qq[i] / p[i];
        if (p[i] < 0) { if (r > t1) return false; if (r > t0) t0 = r; }
        else { if (r < t0) return false; if (r < t1) t1 = r; }
      }
    }
    return t1 - t0 > 1e-6;
  }
  function segRel(s, t) {
    const d = (ax, ay, bx, by, cx, cy) => (bx - ax) * (cy - ay) - (by - ay) * (cx - ax);
    const d1 = d(s.x1, s.y1, s.x2, s.y2, t.x1, t.y1), d2 = d(s.x1, s.y1, s.x2, s.y2, t.x2, t.y2);
    const d3 = d(t.x1, t.y1, t.x2, t.y2, s.x1, s.y1), d4 = d(t.x1, t.y1, t.x2, t.y2, s.x2, s.y2);
    const eps = 1e-6;
    if (Math.abs(d1) < eps && Math.abs(d2) < eps) {
      // collinear: overlapping by more than a couple of pixels?
      const horiz = Math.abs(s.y1 - s.y2) < 0.5;
      const a1 = horiz ? Math.min(s.x1, s.x2) : Math.min(s.y1, s.y2), a2 = horiz ? Math.max(s.x1, s.x2) : Math.max(s.y1, s.y2);
      const b1 = horiz ? Math.min(t.x1, t.x2) : Math.min(t.y1, t.y2), b2 = horiz ? Math.max(t.x1, t.x2) : Math.max(t.y1, t.y2);
      return Math.min(a2, b2) - Math.max(a1, b1) > 3 ? 'overlap' : null;
    }
    if (((d1 > eps && d2 < -eps) || (d1 < -eps && d2 > eps)) && ((d3 > eps && d4 < -eps) || (d3 < -eps && d4 > eps))) return 'cross';
    return null;
  }
};
