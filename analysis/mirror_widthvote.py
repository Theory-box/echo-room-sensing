# Room width from second-order echoes: facing wall j (|off| < 25), an echo at width - ARM*cos(off) (sound to wall j, the
# opposite wall, back). Vote r + ARM*cos(off) over all echoes on each axis (both walls of the pair), leaving out echoes
# that are first-order wall echoes (+-8 cm) and anything below the near wall's distance. The top vote between 1.5 and 7 m
# = width estimate. Compare with the box's own width (sum of the two fitted walls).
import json, math, sys, numpy as np, importlib.util
sys.argv = ['x', 'none']
spec = importlib.util.spec_from_file_location('rf', 'roomfit.py'); rf = importlib.util.module_from_spec(spec); spec.loader.exec_module(rf)
ARM = 0.25
def ad(a, b): return (a - b + 540) % 360 - 180
SESS = ['161659-916','161753-114','161829-437','161910-971','140553-471','121133-233','163656-046','162000-283','140408-771','121421-809','120930-256','123840-246']
for s in SESS:
    try: d = json.load(open(f'logs/sweep-20261118-{s}-sonar_log.json'))
    except Exception: continue
    fr = d['frames']; h = []; r = []
    for x in fr:
        for e in x['e']:
            if e[10] and e[0] > 0.35: h.append(x['h']); r.append(e[0] - (e[12] or 0) / 100)
    p, sc, votes = rf.fit_vote(np.array(h), np.array(r)); rot, D = p[0], p[1:5]; cl = int(len(r) * 0.08 / 4)
    out = []
    for a in (0, 1):
        cand = []
        for x in fr:
            for j in (a, a + 2):
                off = ad(x['h'], rot + 90 * j)
                if abs(off) >= 25: continue
                c = ARM * math.cos(math.radians(off))
                for e in x['e']:
                    v = e[0] + c
                    if any(abs(v - D[k]) < 0.08 for k in range(4)): continue
                    if 1.5 <= v <= 7.0: cand.append(v)
        cand = np.array(cand); bins = np.arange(1.5, 7.0, 0.01)
        hist = np.array([np.sum(np.abs(cand - b) < 0.04) for b in bins]); i = int(np.argmax(hist))
        bg = np.median(hist); box_w = D[a] + D[a + 2]
        hb = int(np.sum(np.abs(cand - box_w) < 0.04))
        out.append(f'axis {a}: box width {box_w:.2f} (walls {D[a]:.2f}{"*" if votes[a]>2*cl else "."}+{D[a+2]:.2f}{"*" if votes[a+2]>2*cl else "."}) | width vote peak {bins[i]:.2f} m ({hist[i]} votes, typical bin {bg:.0f}) | votes at box width {hb}')
    print(s, d['settings']['ping'][:10].ljust(10), ' || '.join(out))
