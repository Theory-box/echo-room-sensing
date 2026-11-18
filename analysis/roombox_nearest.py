# nearbox + (1) ring exclusion as in the app (distance heard >= 3 times in each of >= 9 of 12 sectors, +-3 cm)
# (2) fallback: a wall with no surface above threshold keeps the most-voted peak (as now)
# (3) ghost guard: a farther surface at a predicted multi-bounce distance (from this room's walls, orders 2-3) is a ghost
import json, math, sys, glob, numpy as np, importlib.util
sys.argv = ['x', 'none']
spec = importlib.util.spec_from_file_location('rf', 'roomfit.py'); rf = importlib.util.module_from_spec(spec); spec.loader.exec_module(rf)
import nearbox as NB
ARM = 0.25; ad = NB.ad
def ring_free(h, r):
    secs = {}; cov = set()
    for hh, rr in zip(h, r):
        sc = int((hh % 360) // 30); b = int(round(rr / 0.03)); cov.add(sc)
        for bb in (b - 1, b, b + 1): secs.setdefault(bb, {}).setdefault(sc, 0); secs[bb][sc] += 1
    if len(cov) < 10: return h, r, []
    ring = {b for b, st in secs.items() if sum(1 for c in st.values() if c >= 3) >= 9}
    keep = np.array([int(round(rr / 0.03)) not in ring for rr in r])
    return h[keep], r[keep], sorted(round(b * 0.03, 2) for b in ring)
def ghosts(N):
    """predicted multi-bounce distances (as r + ARM, i.e. from the turning spot) for each wall direction j"""
    g = {}
    for j in range(4):
        a, b = N[j], N[(j + 2) % 4]
        if math.isnan(a): g[j] = []; continue
        L = [2 * a - ARM, 3 * a - 2 * ARM]                        # via you, twice / three times
        if not math.isnan(b): L += [a + b, 2 * a + b, a + 2 * b, 2 * (a + b)]
        g[j] = L
    return g
rows = []
for f in sorted(glob.glob('logs/sweep-20261118-*-sonar_log.json')):
    try: d = json.load(open(f))
    except Exception: continue
    fr = d['frames']; hs = [x['h'] for x in fr]
    if len(fr) < 200 or max(hs) - min(hs) < 300 or d['settings']['ping'] == 'hum': continue
    h = []; r = []
    for x in fr:
        for e in x['e']:
            if len(e) > 12 and e[10] and e[0] > 0.35: h.append(x['h']); r.append(e[0] - (e[12] or 0) / 100)
    h = np.array(h); r = np.array(r)
    if len(r) < 200: continue
    h, r, rings = ring_free(h, r)
    p, sc, votes = rf.fit_vote(h, r); rot = p[0]; D = p[1:5]
    walls, cl = NB.near_fit(h, r, rot)
    N = [pk[0][0] if pk else D[w] for w, pk in enumerate(walls)]
    G = ghosts(N); outside = []; ghost = []
    for w, pk in enumerate(walls):
        for dist, v in pk[1:]:
            (ghost if any(abs(dist - q) < 0.06 for q in G[w]) else outside).append((w, dist, v))
    cur = (min(D[0] + D[2], D[1] + D[3]), max(D[0] + D[2], D[1] + D[3])); new = (min(N[0] + N[2], N[1] + N[3]), max(N[0] + N[2], N[1] + N[3]))
    rows.append((cur, new))
    print(f"{f[19:29]} {d['settings']['ping'][:10]:10s} rings {rings[:3]} | old fit {cur[0]:.2f} x {cur[1]:.2f} | nearest {new[0]:.2f} x {new[1]:.2f} [{' '.join(f'{v:.2f}' for v in N)}] | outside {[(w, x) for w, x, _ in outside]} | ghosts {[(w, x) for w, x, _ in ghost]}")
for k, lab in ((0, 'old fit'), (1, 'nearest surface')):
    a = np.array([x[k][0] for x in rows]); b = np.array([x[k][1] for x in rows])
    print(f'{lab:16s}: short side median {np.median(a):.2f} (p10-p90 {np.percentile(a,10):.2f}-{np.percentile(a,90):.2f}) | long side median {np.median(b):.2f} (p10-p90 {np.percentile(b,10):.2f}-{np.percentile(b,90):.2f}) | long side > 3.5 m in {int(np.sum(b>3.5))}/{len(b)}')
