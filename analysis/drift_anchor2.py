# Face-on anchors v2: a pass (echoes at a locked wall's distance, gaps < 0.6 s) counts if it covers >= SPAN deg of
# heading; its loudest point (level smoothed over +-3 deg) must be >= EDGE deg inside the pass. Anchor = heading at the
# loudest point - locked normal (raw gyro heading). Uses all echoes (passes are short otherwise).
import json, math, sys, numpy as np
import anchor as A
def run(rows_all, KA=0.3, face=35, tol=0.05, SPAN=12, EDGE=3, lockfit=None):
    seen = set(); lock = None; est = 0.0; corr = []; anchors = []; cur = {}
    def close(j):
        p = cur.pop(j, None)
        if not p: return None
        o = np.array([q[0] for q in p]); l = np.array([q[1] for q in p])
        if o.max() - o.min() < SPAN or len(o) < 6: return None
        grid = np.arange(o.min(), o.max() + 0.5, 0.5)
        sm = np.array([np.mean(10 ** (l[np.abs(o - g) <= 3] / 10)) if np.any(np.abs(o - g) <= 3) else 0 for g in grid])
        g = grid[int(np.argmax(sm))]
        if g - o.min() < EDGE or o.max() - g < EDGE: return None
        anchors.append((p[0][2], j, float(g), len(o))); return float(g)
    for k, (t, th, es) in enumerate(rows_all):
        if lock is None:
            seen.add(int((th % 360) // 30))
            if len(seen) >= 11:
                p, sc, v = A.fit(rows_all[:k + 1]); cl = sum(len(e) for _, _, e in rows_all[:k + 1]) * 0.08 / 4
                lock = (p[0], p[1:5], [vv > 2 * cl for vv in v])
            corr.append(0.0); continue
        rot, D, ok = lock
        for j in range(4):
            if not ok[j]: continue
            off_raw = A.ad(th, rot + 90 * j)
            if j in cur and t - cur[j][-1][2] > 0.6:
                a = close(j)
                if a is not None: est += KA * (a - est)
            if abs(off_raw - est) >= face: continue
            pred = D[j] - A.ARM * math.cos(math.radians(off_raw - est))
            for v, l in es:
                if abs(v - pred) < tol: cur.setdefault(j, []).append((off_raw, l, t))
        corr.append(est)
    return corr, anchors, lock
def rows_all(fr):
    T0 = fr[0]['t']
    return [((x['t'] - T0) / 1000, x['h'], [(e[0] - ((e[12] or 0) / 100 if len(e) > 12 else 0), e[1]) for e in x['e'] if e[0] > 0.35]) for x in fr]
if __name__ == '__main__':
    for s in ['184525-732', '184843-704', '185155-137', '185319-472', '185606-164', '173253-126', '173415-011', '121133-233', '161659-916', '161753-114', '161910-971', '140553-471', '163656-046', '120930-256']:
        try: d = json.load(open(f'logs/sweep-20261118-{s}-sonar_log.json'))
        except Exception: continue
        ra = rows_all(d['frames']); rc = A.rows_of(d['frames']); T = ra[-1][0]
        corr, An, lock = run(ra)
        if lock is None: continue
        resid = [An[i][2] - np.median([An[k][2] for k in range(max(0, i - 3), min(len(An), i + 4)) if k != i]) for i in range(len(An))] if len(An) >= 4 else []
        f0 = A.fit(rc, None, 0, 60); f1 = A.fit(rc, None, T - 60, T); g1 = A.fit(rc, corr, T - 60, T); raw = A.fit(rc); cor = A.fit(rc, corr)
        rot = lambda f: f[0][0] if f else float('nan')
        print(f"{s} {d['settings']['ping'][:10]:10s} {T:4.0f}s | anchors {len(An):2d} (t:wall:deg) " + ' '.join(f'{x[0]:.0f}:{x[1]}:{x[2]:+.0f}' for x in An[:14]) +
              (f" | scatter {np.std(resid):.1f}" if resid else '') + f" | est end {corr[-1]:+.1f} | box rot 1st min {rot(f0):+.0f}, last min raw {rot(f1):+.0f} -> corr {rot(g1):+.0f} | one-box {raw[1]} -> {cor[1]}")
