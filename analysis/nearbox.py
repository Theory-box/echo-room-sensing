# Box with openings: per wall, candidate distances = peaks of the facing-echo histogram (+-4 cm window). A peak counts
# as a surface if its votes > max(2 x clutter level, 30% of that wall's best peak). The NEAREST surface is this room's
# wall (nothing behind a solid wall is heard); farther surfaces = another room seen through an opening (outside lines).
# Rotation: as now (most echoes explained by the best peaks). Compare with the current fit (most-voted peak per wall).
import json, math, sys, glob, numpy as np, importlib.util
sys.argv = ['x', 'none']
spec = importlib.util.spec_from_file_location('rf', 'roomfit.py'); rf = importlib.util.module_from_spec(spec); spec.loader.exec_module(rf)
ARM = 0.25
def ad(a, b): return (a - b + 540) % 360 - 180
def near_fit(h, r, rot, face=30, tol=0.04, frac=0.3):
    bins = np.arange(0.35, 5.0, 0.01); cl = len(r) * 0.08 / 4; walls = []
    for w in range(4):
        n = rot + 90 * w; off = np.array([ad(x, n) for x in h]); m = np.abs(off) < face
        cand = r[m] + ARM * np.cos(np.radians(off[m]))
        hist = np.array([np.sum(np.abs(cand - b) < tol) for b in bins])
        best = hist.max(); thr = max(2 * cl, frac * best); peaks = []
        for i in range(len(bins)):
            if hist[i] >= thr and hist[i] == hist[max(0, i - 8):i + 9].max():
                if not peaks or bins[i] - peaks[-1][0] > 0.12: peaks.append((round(float(bins[i]), 2), int(hist[i])))
        walls.append(peaks)
    return walls, cl
rows = []
for f in sorted(glob.glob('logs/sweep-20261118-*-sonar_log.json')):
    try: d = json.load(open(f))
    except Exception: continue
    fr = d['frames']; hs = [x['h'] for x in fr]
    if len(fr) < 200 or max(hs) - min(hs) < 300 or d['settings']['ping'] in ('hum',): continue
    h = []; r = []
    for x in fr:
        for e in x['e']:
            if len(e) > 12 and e[10] and e[0] > 0.35: h.append(x["h"]); r.append(e[0] - (e[12] or 0) / 100)
    h = np.array(h); r = np.array(r)
    if len(r) < 200: continue
    p, sc, votes = rf.fit_vote(h, r); rot = p[0]; D = p[1:5]
    walls, cl = near_fit(h, r, rot)
    N = [pk[0][0] if pk else float('nan') for pk in walls]
    cur = (min(D[0] + D[2], D[1] + D[3]), max(D[0] + D[2], D[1] + D[3])); new = (min(N[0] + N[2], N[1] + N[3]), max(N[0] + N[2], N[1] + N[3]))
    outside = [(w, pk[1:]) for w, pk in enumerate(walls) if len(pk) > 1]
    rows.append((f[19:29], d['settings']['ping'][:10], cur, new))
    print(f"{f[19:29]} {d['settings']['ping'][:10]:10s} current {cur[0]:.2f} x {cur[1]:.2f} [{' '.join(f'{v:.2f}' for v in D)}] | nearest-surface {new[0]:.2f} x {new[1]:.2f} [{' '.join(f'{v:.2f}' for v in N)}] | outside lines {outside}")
import statistics as st
for k, lab in ((2, 'current'), (3, 'nearest-surface')):
    a = [x[k][0] for x in rows if not math.isnan(x[k][0])]; b = [x[k][1] for x in rows if not math.isnan(x[k][1])]
    print(f'{lab:16s}: short side median {st.median(a):.2f} m, spread (p10-p90) {np.percentile(a,10):.2f}-{np.percentile(a,90):.2f} | long side median {st.median(b):.2f}, spread {np.percentile(b,10):.2f}-{np.percentile(b,90):.2f} | long side > 3.5 m in {sum(v>3.5 for v in b)}/{len(b)}')
