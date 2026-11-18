# Direction of each tracked echo from rough phone motion, offline prototype.
# Per track, over the last WIN s: r(t) = c0 + c1 t + c2 t^2 - (uE xE(t) + uN xN(t)), where x = acceleration integrated twice
# from the window start (unknown start velocity -> c1, sensor offset/bias -> c2). u = unit-ish vector toward the reflector.
import json, math, sys, collections
import numpy as np

def load(f):
    d = json.load(open(f)); fr = d['frames']
    A = np.array([a for x in fr for a in x.get('ac', [])], float)
    A = A[np.argsort(A[:, 0])]
    return d, fr, A

def disp_at(A, t_start, ts):
    """double integral of (aE, aN) from t_start, evaluated at times ts (ms). returns (n,2) metres"""
    m = (A[:, 0] >= t_start - 20) & (A[:, 0] <= ts.max() + 20)
    S = A[m]
    if len(S) < 10: return None
    t = S[:, 0] / 1000; a = S[:, 1:3]
    dt = np.diff(t, prepend=t[0])
    v = np.cumsum(a * dt[:, None], axis=0)
    x = np.cumsum(v * dt[:, None], axis=0)
    return np.column_stack([np.interp(ts / 1000, t, x[:, 0]), np.interp(ts / 1000, t, x[:, 1])])

def run(f, offset_ms=240, WIN=3000, zthr=2.5, minN=20, GATE=0.04):
    d, fr, A = load(f)
    hist = collections.defaultdict(list)     # tid -> [(tc, r)]
    out = []   # (frame index, echo, verdict dict)
    for i, x in enumerate(fr):
        tc = x['tc']; psi = math.radians(x['yaw'] + 180); fE, fN = math.sin(psi), math.cos(psi)
        for e in x['e']:
            if not e[9]: continue
            r = e[0] - (e[12] / 100 if len(e) > 12 and e[12] is not None else 0)
            # history by distance: per earlier reading in the window, the detection closest to this one (within GATE),
            # following the echo as it drifts (gate around the previous member)
            h = []; ref = r
            for j in range(i, -1, -1):
                y = fr[j]
                if tc - y['tc'] > WIN: break
                cand = [(abs((q[0] - (q[12] / 100 if len(q) > 12 and q[12] is not None else 0)) - ref), q) for q in y['e']]
                cand = [cq for cq in cand if cq[0] < GATE]
                if cand:
                    q = min(cand, key=lambda z: z[0])[1]; rq = q[0] - (q[12] / 100 if len(q) > 12 and q[12] is not None else 0)
                    h.append((y['tc'], rq)); ref = rq
            h.reverse()
            if len(h) < minN or not e[10]: out.append((i, e, None)); continue
            ts = np.array([p[0] for p in h], float); rs = np.array([p[1] for p in h])
            X = disp_at(A, ts[0] - offset_ms, ts - offset_ms)
            if X is None: out.append((i, e, None)); continue
            tt = (ts - ts[0]) / 1000
            M = np.column_stack([np.ones_like(tt), tt, tt * tt, -X[:, 0], -X[:, 1]])
            c, res, rk, _ = np.linalg.lstsq(M, rs, rcond=None)
            if rk < 5: out.append((i, e, None)); continue
            dof = max(1, len(rs) - 5); s2 = ((rs - M @ c) ** 2).sum() / dof
            cov = s2 * np.linalg.pinv(M.T @ M)
            uE, uN = c[3], c[4]; uf = uE * fE + uN * fN
            vf = fE * fE * cov[3, 3] + 2 * fE * fN * cov[3, 4] + fN * fN * cov[4, 4]
            # how much forward motion there was in the window (after removing the quadratic)
            xf = X[:, 0] * fE + X[:, 1] * fN; Q = np.column_stack([np.ones_like(tt), tt, tt * tt])
            xr = xf - Q @ np.linalg.lstsq(Q, xf, rcond=None)[0]
            out.append((i, e, dict(uf=uf, z=uf / math.sqrt(vf) if vf > 0 else 0, mot=xr.std() * 100, res=math.sqrt(s2) * 100)))
    return d, fr, out

def tally(sel, zthr=2.5):
    c = collections.Counter()
    for v in sel:
        if v is None: c['none'] += 1
        elif v['z'] > zthr: c['ahead'] += 1
        elif v['z'] < -zthr: c['behind'] += 1
        else: c['unsure'] += 1
    return dict(c)

if __name__ == '__main__':
    f = sys.argv[1]
    for off in (0, 120, 240, 360):
        d, fr, out = run(f, off)
        T0 = fr[0]['t']
        w = [v for i, e, v in out if abs(e[0] - 0.9) < 0.15 and 10000 <= fr[i]['t'] - T0 < 30000]
        far = [v for i, e, v in out if abs(e[0] - 3.8) < 0.15 and 10000 <= fr[i]['t'] - T0 < 30000]
        ufs = sorted(v['uf'] for v in w if v)
        print(f'offset {off} ms: wall 0.9 m (ahead): {tally(w)} median fwd part {ufs[len(ufs)//2] if ufs else None:.2f} | 3.8 m echo: {tally(far)}')
