# Fit a box room to all echo detections of a sweep: 4 perpendicular walls (distances from your turning spot, and the
# box's rotation). A wall is heard when the phone faces it roughly squarely; then its echo distance is
# D_j - ARM*cos(heading - normal_j). Each detection is explained by the best-fitting wall (or by "clutter" if none fits
# within a tolerance); the box parameters minimise a robust cost. Reports per-wall support (how many detections back it).
import numpy as np, json, math, sys
from scipy.optimize import minimize
ARM = 0.25
def ad(a, b): return (a - b + 540) % 360 - 180
def predict(params, h):
    """params: rot (deg), D0..D3 (m, from the turning spot to each wall along its normal); h: heading (deg).
    returns (4, len(h)) predicted echo distances, and a facing mask (|h - normal| < 35 deg)"""
    rot, D = params[0], params[1:5]
    normals = rot + np.array([0, 90, 180, 270])
    off = np.array([ad(h, n) for n in normals])
    r = D[:, None] - ARM * np.cos(np.radians(off))
    return r, np.abs(off) < 35, off
def cost(params, h, r, tol=0.06):
    pr, face, _ = predict(params, h)
    err = np.where(face, np.abs(pr - r[None, :]), 9.0)
    e = err.min(0)
    return np.sum(np.minimum(e, tol) ** 2)          # robust: errors beyond tol count as "clutter" (capped)
def fit(h, r, tries=60, seed=0):
    rng = np.random.default_rng(seed); best = None
    for _ in range(tries):
        p0 = np.r_[rng.uniform(-45, 45), rng.uniform(0.5, 4.0, 4)]
        res = minimize(cost, p0, args=(h, r), method='Nelder-Mead', options={'maxiter': 3000, 'xatol': 1e-4, 'fatol': 1e-7})
        if best is None or res.fun < best.fun: best = res
    p = best.x.copy(); p[0] = ((p[0] + 45) % 90) - 45
    return p, best.fun
def support(params, h, r, tol=0.06):
    pr, face, off = predict(params, h)
    err = np.where(face, np.abs(pr - r[None, :]), 9.0); j = err.argmin(0); ok = err.min(0) < tol
    return [int(np.sum(ok & (j == w))) for w in range(4)], float(np.mean(ok))
def canon(p):
    """order walls by their normal direction relative to heading 0 so different fits compare"""
    rot = p[0]; D = p[1:5]; n = (rot + np.array([0, 90, 180, 270])) % 360
    o = np.argsort(n); return n[o], D[o]
if __name__ == '__main__' and sys.argv[1] == 'sim':
    rng = np.random.default_rng(1)
    true = np.array([12.0, 1.1, 2.3, 1.7, 3.0])   # rotation, walls
    h = np.concatenate([np.linspace(-180, 180, 600) + rng.normal(0, 2, 600) for _ in range(2)])
    pr, face, off = predict(true, h)
    det_h, det_r = [], []
    for i in range(len(h)):
        for w in range(4):
            if face[w, i] and rng.random() < 0.5 * math.cos(math.radians(off[w, i])) ** 4:
                det_h.append(h[i]); det_r.append(pr[w, i] + rng.normal(0, 0.015))
        for _ in range(rng.poisson(1.0)):           # clutter / fakes
            det_h.append(h[i]); det_r.append(rng.uniform(0.4, 4.0))
    det_h, det_r = np.array(det_h), np.array(det_r)
    p, f = fit(det_h, det_r)
    print('truth : rot %.1f, walls %s' % (true[0], np.round(true[1:], 3)))
    print('fitted: rot %.1f, walls %s' % (p[0], np.round(p[1:], 3)), '| support', support(p, det_h, det_r))
    # what does it do with a room that is NOT a box (one wall missing: open side)?
    keep = ~((np.abs(np.array([ad(x, true[0] + 180) for x in det_h])) < 35) & (np.abs(det_r - (true[3] - ARM * np.cos(np.radians(np.array([ad(x, true[0] + 180) for x in det_h]))))) < 0.05))
    p2, f2 = fit(det_h[keep], det_r[keep])
    print('open side (wall 3 removed): fitted walls %s | support per wall %s' % (np.round(p2[1:], 3), support(p2, det_h[keep], det_r[keep])[0]))

def fit_vote(h, r, tol=0.04, rmin=0.35, rmax=5.0, face_deg=30, w_level=None):
    """for each rotation (1 deg steps over 90 deg), each wall's distance = the most-voted value of r + ARM*cos(off)
    among detections facing it; score = detections explained. Returns params, score, per-wall votes."""
    best = None; bins = np.arange(rmin, rmax, 0.01)
    for rot in np.arange(-45, 45, 1.0):
        D = []; votes = []; tot = 0
        for w in range(4):
            n = rot + 90 * w; off = np.array([ad(x, n) for x in h]); m = np.abs(off) < face_deg
            if m.sum() < 3: D.append(np.nan); votes.append(0); continue
            cand = r[m] + ARM * np.cos(np.radians(off[m]))
            hist = np.array([np.sum(np.abs(cand - b) < tol) for b in bins])
            i = int(np.argmax(hist)); D.append(bins[i]); votes.append(int(hist[i])); tot += hist[i]
        if best is None or tot > best[1]: best = (np.r_[rot, D], tot, votes)
    return best
if __name__ == '__main__' and sys.argv[1] == 'sim2':
    rng = np.random.default_rng(1)
    for case in ('box', 'open side', 'L-shaped (one wall split)'):
        true = np.array([12.0, 1.1, 2.3, 1.7, 3.0])
        h = np.concatenate([np.linspace(-180, 180, 600) + rng.normal(0, 2, 600) for _ in range(2)])
        pr, face, off = predict(true, h)
        dh, dr = [], []
        for i in range(len(h)):
            for w in range(4):
                if case == 'open side' and w == 2: continue
                d = pr[w, i]
                if case.startswith('L') and w == 1 and off[w, i] > 0: d = d + 0.8      # half of that wall is 0.8 m farther
                if face[w, i] and rng.random() < 0.5 * math.cos(math.radians(off[w, i])) ** 4:
                    dh.append(h[i]); dr.append(d + rng.normal(0, 0.015))
            for _ in range(rng.poisson(1.0)): dh.append(h[i]); dr.append(rng.uniform(0.4, 4.0))
        dh, dr = np.array(dh), np.array(dr)
        p, score, votes = fit_vote(dh, dr)
        print(f'{case:26s}: truth rot 12, walls {true[1:]} | fitted rot {p[0]:.0f}, walls {np.round(p[1:],2)}, votes per wall {votes} (clutter-only level ~{int(len(dr)*0.08/4)})')
