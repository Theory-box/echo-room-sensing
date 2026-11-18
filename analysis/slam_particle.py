# Particle filter (Monte Carlo localisation) against the locked room box -- no walking flag.
# N guesses of where you stand. Each reading: every guess moves a little at random (most small, a few large jumps so
# the filter can catch up after you walk), then is scored by how well ALL the echoes fit the box from there:
#   per echo: eps + sum over facing walls of exp(-(r - predicted)^2 / 2 sigma^2)   (eps = "this echo is clutter")
# Guesses resampled in proportion to their score. Estimate = weighted mean of the guesses.
import math, sys, numpy as np
import slam5 as B
S = B.S; ad = S.ad; ARM = S.ARM; M = B.M
class PF:
    def __init__(self, rot, W, votes=None, cl=0, n=300, sig=0.02, eps=0.3, q=0.10, jump=0.02, jsig=0.25, face=30, seed=1):
        self.rng = np.random.default_rng(seed); self.rot = rot; self.W = np.array(W, float)
        self.ok = [True] * 4 if votes is None else [v > 2 * cl for v in votes]
        self.Nv = np.array([[math.sin(math.radians(rot + 90 * j)), math.cos(math.radians(rot + 90 * j))] for j in range(4)])
        self.n, self.sig, self.eps, self.q, self.jump, self.jsig, self.face = n, sig, eps, q, jump, jsig, face
        self.X = self.rng.normal(0, 0.01, (n, 2)); self.w = np.full(n, 1 / n); self.t = None; self.p = np.zeros(2)
    def step(self, t, theta, dets, walking=None):
        dt = 0.0 if self.t is None else max(0.0, t - self.t); self.t = t
        if dt > 0:
            self.X += self.rng.normal(0, self.q * math.sqrt(dt), self.X.shape)
            J = self.rng.random(self.n) < self.jump * dt * 10           # a few guesses jump (per 0.1 s)
            self.X[J] += self.rng.normal(0, self.jsig, (J.sum(), 2))
        walls = [j for j in range(4) if self.ok[j] and abs(ad(theta, self.rot + 90 * j)) < self.face]
        if walls and dets:
            logw = np.zeros(self.n)
            for r in dets:
                lik = np.full(self.n, self.eps)
                for j in walls:
                    off = math.radians(ad(theta, self.rot + 90 * j))
                    pred = self.W[j] - self.X @ self.Nv[j] - ARM * math.cos(off)
                    lik += np.exp(-0.5 * ((r - pred) / self.sig) ** 2)
                logw += np.log(lik)
            lw = np.log(self.w + 1e-300) + logw; lw -= lw.max(); w = np.exp(lw); self.w = w / w.sum()
            if 1 / np.sum(self.w ** 2) < self.n / 2:                    # resample (systematic)
                c = np.cumsum(self.w); u = (self.rng.random() + np.arange(self.n)) / self.n
                self.X = self.X[np.minimum(np.searchsorted(c, u), self.n - 1)]; self.w = np.full(self.n, 1 / self.n)
        self.p = self.w @ self.X
        return self.p.copy()
def same_spot(**kw):
    out = []
    for s in ['161659-916', '161753-114', '161910-971', '140553-471', '121133-233', '162000-283', '162107-513', '141954-224']:
        d, rows = S.detections(f'logs/sweep-20261118-{s}-sonar_log.json')
        seen = set(); tlock = None
        for t, th, dets, _ in rows:
            seen.add(int((th % 360) // 30))
            if len(seen) >= 11: tlock = t; break
        if tlock is None: continue
        rot, W, votes, cl = S.fit_box(rows, tlock)
        tr = PF(rot, W, votes, cl, **kw); P = []
        for t, th, dets, _ in rows:
            if t <= tlock: continue
            P.append(tr.step(t, th, dets))
        P = np.array(P); out.append(f'{100*np.max(np.hypot(P[:,0],P[:,1])):.0f}')
    return ' '.join(out) + ' cm'
def sims(seeds=(5, 6, 7), **kw):
    res = {}
    for sd in seeds:
        M.rng = np.random.default_rng(sd)
        for name, fn in M.FNS.items():
            rows = M.sim_rows(fn, 44)
            rot, W, votes, cl = S.fit_box(rows, 20)
            tr = PF(rot, W, votes, cl, **kw); E = []
            for t, th, dets, _ in rows:
                p = tr.step(t, th, dets)
                if t > 20: E.append(np.linalg.norm(p - fn(t)[0]))
            res.setdefault(name, []).extend(E)
    return ' | '.join(f'{n}: med {100*np.median(E):.0f} p90 {100*np.percentile(E,90):.0f}' for n, E in res.items()) + ' cm'
if __name__ == '__main__':
    import slam7
    M.FNS['walk + sweep 90'] = slam7.walk_d
    grid = [dict(), dict(eps=0.1), dict(eps=1.0), dict(q=0.2), dict(jump=0.05), dict(jump=0.0), dict(sig=0.03)]
    for kw in grid:
        print('PF', kw, '\n   same-spot max drift:', same_spot(**kw), '\n   sims:', sims(**kw), flush=True)
