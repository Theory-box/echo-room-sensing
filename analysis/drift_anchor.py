# Face-on anchors: each time the sweep passes across a locked wall, the echo is loudest straight-on. A pass = run of
# readings (gaps < 0.6 s) with an echo within 5 cm of that wall's predicted distance and heading within 35 deg of its
# normal. Only passes that swing across both sides of straight-on (offsets reach <= -8 and >= +8 deg, >= 5 echoes)
# count. Anchor = loudness-weighted mean of (heading - normal) over the pass = how far the gyro heading is off.
# Drift estimate: each anchor pulls the estimate KA of the way toward it. Corrected heading = heading - estimate.
# Checks: (1) anchors' spread around their own smooth trend (noise); (2) the box fitted on the first minute vs the
# last minute, raw vs corrected (should agree if headings stay consistent); (3) echoes explained by one box.
import json, math, sys, numpy as np, importlib.util
sys.argv = ['x', 'none']
spec = importlib.util.spec_from_file_location('rf', 'roomfit.py'); rf = importlib.util.module_from_spec(spec); spec.loader.exec_module(rf)
ARM = 0.25
def ad(a, b): return (a - b + 540) % 360 - 180
def rows_of(fr):
    T0 = fr[0]['t']; out = []
    for x in fr:
        es = [(e[0] - (e[12] or 0) / 100, e[1]) for e in x['e'] if len(e) > 12 and e[10] and e[0] > 0.35]
        out.append(((x['t'] - T0) / 1000, x['h'], es))
    return out
def fit(rows, corr=None, t0=0, t1=1e9):
    h = []; r = []
    for k, (t, th, es) in enumerate(rows):
        if t0 <= t < t1:
            for v, _ in es: h.append(th - (corr[k] if corr is not None else 0)); r.append(v)
    return rf.fit_vote(np.array(h), np.array(r)) if len(r) >= 60 else None
def anchors_run(rows, KA=0.3, face=35, tol=0.05, side=8, need=5, lock_rows=None):
    seen = set(); lock = None; est = 0.0; corr = []; anchors = []; cur = {}
    def close(j):
        p = cur.pop(j, None)
        if not p: return
        offs = np.array([o for o, _ in p['e']]); w = np.array([10 ** (l / 10) for _, l in p['e']])
        if len(offs) >= need and offs.min() <= -side and offs.max() >= side:
            anchors.append((p['t'], j, float((w * offs).sum() / w.sum()), len(offs)))
            return anchors[-1][2]
    for k, (t, th, es) in enumerate(rows):
        if lock is None:
            seen.add(int((th % 360) // 30))
            if len(seen) >= 11:
                p, sc, v = fit(rows[:k + 1]); cl = sum(len(e) for _, _, e in rows[:k + 1]) * 0.08 / 4
                lock = (p[0], p[1:5], [vv > 2 * cl for vv in v])
            corr.append(0.0); continue
        rot, D, ok = lock
        for j in range(4):
            if not ok[j]: continue
            off_raw = ad(th, rot + 90 * j)            # raw heading vs locked normal (anchors measure the raw offset)
            if abs(off_raw - est) >= face:
                if j in cur and t - cur[j]['last'] > 0.6:
                    a = close(j)
                    if a is not None: est += KA * (a - est)
                continue
            pred = D[j] - ARM * math.cos(math.radians(off_raw - est))
            hit = [(off_raw, l) for v, l in es if abs(v - pred) < tol]
            if j in cur and t - cur[j]['last'] > 0.6:
                a = close(j)
                if a is not None: est += KA * (a - est)
            if hit:
                c = cur.setdefault(j, {'t': t, 'last': t, 'e': []}); c['e'] += hit; c['last'] = t
        corr.append(est)
    return corr, anchors, lock
if __name__ == '__main__':
    for s in ['184525-732', '184843-704', '185155-137', '185319-472', '185606-164', '173253-126', '173415-011', '121133-233', '161659-916', '161753-114', '161910-971', '140553-471', '163656-046', '120930-256']:
        try: d = json.load(open(f'logs/sweep-20261118-{s}-sonar_log.json'))
        except Exception: continue
        rows = rows_of(d['frames']); T = rows[-1][0]
        corr, A, lock = anchors_run(rows)
        if lock is None: continue
        a = np.array([x[2] for x in A]) if A else np.array([])
        # noise: spread of anchors around a running median of neighbours
        resid = [A[i][2] - np.median([A[k][2] for k in range(max(0, i - 3), min(len(A), i + 4)) if k != i]) for i in range(len(A))] if len(A) >= 4 else []
        raw = fit(rows); cor = fit(rows, corr)
        f0 = fit(rows, None, 0, 60); f1 = fit(rows, None, T - 60, T); g1 = fit(rows, corr, T - 60, T)
        rot = lambda f: f[0][0] if f else float('nan')
        print(f"{s} {d['settings']['ping'][:10]:10s} {T:4.0f}s | anchors {len(A):2d}: " + ' '.join(f'{x[2]:+.0f}' for x in A[:16]) +
              (f" | scatter {np.std(resid):.1f} deg" if resid else '') + f" | final est {corr[-1]:+.1f} | box rot first min {rot(f0):+.0f}, last min raw {rot(f1):+.0f} -> corrected {rot(g1):+.0f} | one-box echoes {raw[1]} -> {cor[1]}")
