# slam6 + standing recovery: rejected echoes (|innov| > gate, within reach) are kept for `rhold` s per axis; if >= `rneed`
# of them agree within `ragree` m AND outnumber the echoes accepted on that axis in the same window, apply their mean.
import math, numpy as np
import slam5 as B, slam6 as C
S = B.S; ad = S.ad; ARM = S.ARM
class T7(C.T6):
    def __init__(self, *a, rhold=2.0, rneed=3, ragree=0.04, reach=1.0, **k):
        super().__init__(*a, **k); self.rhold, self.rneed, self.ragree, self.reach = rhold, rneed, ragree, reach
        self.rp = [[], []]; self.acc = [[], []]; self.snaps = 0
    def _apply(self, v, a, t):
        super()._apply(v, a, t); self.acc[a].append(t)
    def step(self, t, theta, dets, walking):
        dt = 0 if self.t is None else max(0.0, t - self.t); self.t = t
        self.P += np.eye(2) * (self.qw if walking else self.qs) * dt
        for r in dets:
            best = None; far = None
            for j in range(4):
                if not self.ok[j]: continue
                off = ad(theta, self.rot + 90 * j)
                if abs(off) >= 30: continue
                z = self.W[j] - r - ARM * math.cos(math.radians(off)); a = j % 2; v = z if j < 2 else -z
                g = self.gate + (min(self.gmax, self.vmax * (t - self.lastax[a])) if walking else 0)
                innov = v - self.N[a] @ self.x[:2]
                if abs(innov) < g and (best is None or abs(innov) < abs(best[0])): best = (innov, v, a)
                elif abs(innov) < self.reach and (far is None or abs(innov) < abs(far[0])): far = (innov, v, a)
            if best is not None:
                innov, v, a = best
                if abs(innov) <= self.gate: self._apply(v, a, t); continue
                self.pend[a] = [(tp, vp) for tp, vp in self.pend[a] if t - tp < self.hold]
                m = [vp for tp, vp in self.pend[a] if abs(vp - v) < self.agree]
                if m: self._apply((sum(m) + v) / (len(m) + 1), a, t); self.pend[a] = []; continue
                self.pend[a].append((t, v)); far = best
            self.rej += 1
            if far is None: continue
            innov, v, a = far
            self.rp[a] = [(tp, vp) for tp, vp in self.rp[a] if t - tp < self.rhold] + [(t, v)]
            self.acc[a] = [tp for tp in self.acc[a] if t - tp < self.rhold]
            vs = np.array([vp for _, vp in self.rp[a]]); cnt = np.array([np.sum(np.abs(vs - c) < self.ragree) for c in vs]); i = int(np.argmax(cnt))
            if cnt[i] >= self.rneed and cnt[i] > len(self.acc[a]):
                mval = float(np.mean(vs[np.abs(vs - vs[i]) < self.ragree])); cur = self.N[a] @ self.x[:2]
                self.x[:2] = self.x[:2] + self.N[a] * (mval - cur); self.rp[a] = []; self.snaps += 1; self.lastax[a] = t
        return self.x[:2].copy()
def walk_d(t):   # like the app sim case 3: walk 0.6 m toward a wall in 4 s while sweeping +-90 (3 s period), then stand & sweep
    if t < 20: return np.zeros(2), (t / 20) * 720 % 360 - 180
    s = min(1.0, (t - 20) / 4); return np.array([0.08, 0.6]) * s, 90 * math.sin(2 * math.pi * (t - 20) / 3)
B.M.FNS['walk + sweep 90'] = walk_d
def run(**kw):
    orig = B.T5; B.T5 = lambda *x, **k: T7(*x, **k)
    try: return B.same_spot(**kw), B.sims(**kw)
    finally: B.T5 = orig
print('slam6 (no standing recovery):'); orig = B.T5; B.T5 = lambda *x, **k: C.T6(*x, hold=1.0, agree=0.06, **k); print('  ', B.same_spot(), '\n  ', B.sims()); B.T5 = orig
for kw in (dict(), dict(rneed=4), dict(rneed=5), dict(rhold=3.0, rneed=4), dict(ragree=0.03, rneed=4)):
    a, b = run(hold=1.0, agree=0.06, **kw); print('recovery', kw, '\n   same-spot max drift:', a, '\n   sims:', b)
