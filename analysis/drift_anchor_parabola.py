# Face-on from geometry: within a pass across a locked wall, r(off) = D - ARM*cos(off - delta). Fit delta (and D) by
# grid search (least squares, robust: errors capped at 3 cm). Compare scatter of anchors with the loudness method.
import json, math, numpy as np
import anchor as A, anchor2 as B
def passes(rows, lock, face=40, tol=0.06, gap=0.6):
    rot, D, ok = lock; cur = {}; out = []
    for t, th, es in rows:
        for j in range(4):
            if not ok[j]: continue
            off = A.ad(th, rot + 90 * j)
            if j in cur and t - cur[j][-1][3] > gap: out.append((j, cur.pop(j)))
            if abs(off) >= face: continue
            pred = D[j] - A.ARM * math.cos(math.radians(off))
            for v, l in es:
                if abs(v - pred) < tol: cur.setdefault(j, []).append((off, v, l, t))
    out += list(cur.items()); return out
def geo(p):
    o = np.array([q[0] for q in p]); r = np.array([q[1] for q in p])
    best = None
    for dl in np.arange(-25, 25.1, 0.5):
        m = r + A.ARM * np.cos(np.radians(o - dl)); Dh = np.median(m); e = np.minimum(np.abs(m - Dh), 0.03)
        c = np.sum(e ** 2)
        if best is None or c < best[0]: best = (c, dl)
    return best[1]
def loud(p):
    o = np.array([q[0] for q in p]); l = np.array([q[2] for q in p]); best = None
    for g in np.arange(o.min(), o.max() + 0.5, 0.5):
        m = np.abs(o - g) <= 3
        if m.any():
            v = np.mean(10 ** (l[m] / 10))
            if best is None or v > best[0]: best = (v, g)
    return best[1]
allg = []; alll = []
for s in ['184525-732', '184843-704', '185155-137', '185319-472', '185606-164', '121133-233', '161659-916', '161753-114', '161910-971', '140553-471', '163656-046', '120930-256']:
    try: d = json.load(open(f'logs/sweep-20261118-{s}-sonar_log.json'))
    except Exception: continue
    ra = B.rows_all(d['frames']); p, sc, v = A.fit(ra); cl = sum(len(e) for _, _, e in ra) * 0.08 / 4
    lock = (p[0], p[1:5], [vv > 2 * cl for vv in v])
    G = []; L = []
    for j, P in passes(ra, lock):
        o = [q[0] for q in P]
        if len(P) < 8 or max(o) - min(o) < 15: continue
        G.append((j, geo(P))); L.append((j, loud(P)))
    # per wall, spread of anchors (same wall, same session: true drift small over a minute or two)
    def spread(X):
        out = []
        for j in range(4):
            a = [x for k, x in X if k == j]
            if len(a) >= 2: out.append(np.std(a))
        return np.mean(out) if out else float('nan')
    allg += [x for _, x in G]; alll += [x for _, x in L]
    print(f"{s}: passes {len(G)} | geometry anchors {' '.join(f'{j}:{x:+.0f}' for j, x in G[:10])} (spread per wall {spread(G):.1f}) | loudness {' '.join(f'{j}:{x:+.0f}' for j, x in L[:10])} (spread {spread(L):.1f})")
print(f'ALL: geometry anchors sd {np.std(allg):.1f} deg (n {len(allg)}), loudness sd {np.std(alll):.1f} deg')
