# slam5 + confirmation: an echo whose innovation exceeds the standing gate is held; it is applied only if another echo on
# the same axis within `hold` s agrees within `agree` m (then both are applied, as their mean).
import math, numpy as np
import slam5 as B
S = B.S; ad = S.ad; ARM = S.ARM
class T6(B.T5):
    def __init__(self, *a, hold=0.6, agree=0.04, **k):
        super().__init__(*a, **k); self.hold, self.agree = hold, agree; self.pend = [[], []]
    def _apply(self, v, a, t):
        H = np.zeros(len(self.x)); H[:2] = self.N[a]; innov = v - H @ self.x; Sv = H @ self.P @ H + self.sr2; K = self.P @ H / Sv
        self.x = self.x + K * innov; self.P = self.P - np.outer(K, H) @ self.P; self.used += 1; self.lastax[a] = t
    def step(self, t, theta, dets, walking):
        dt = 0 if self.t is None else max(0.0, t - self.t); self.t = t
        self.P += np.eye(2) * (self.qw if walking else self.qs) * dt
        for r in dets:
            best = None
            for j in range(4):
                if not self.ok[j]: continue
                off = ad(theta, self.rot + 90 * j)
                if abs(off) >= 30: continue
                z = self.W[j] - r - ARM * math.cos(math.radians(off)); a = j % 2; v = z if j < 2 else -z
                g = self.gate + (min(self.gmax, self.vmax * (t - self.lastax[a])) if walking else 0)
                innov = v - self.N[a] @ self.x[:2]
                if abs(innov) < g and (best is None or abs(innov) < abs(best[0])): best = (innov, v, a)
            if best is None: self.rej += 1; continue
            innov, v, a = best
            if abs(innov) <= self.gate: self._apply(v, a, t); continue
            self.pend[a] = [(tp, vp) for tp, vp in self.pend[a] if t - tp < self.hold]
            m = [vp for tp, vp in self.pend[a] if abs(vp - v) < self.agree]
            if m: self._apply((sum(m) + v) / (len(m) + 1), a, t); self.pend[a] = []
            else: self.pend[a].append((t, v)); self.rej += 1
        return self.x[:2].copy()
B.T5_orig = B.T5
def run(cls, **kw):
    B.T5 = cls
    try: return B.same_spot(**kw), B.sims(**kw)
    finally: B.T5 = B.T5_orig
for kw in (dict(), dict(hold=1.0), dict(agree=0.06), dict(hold=1.0, agree=0.06), dict(vmax=1.0, hold=1.0)):
    a, b = run(lambda *x, **k: T6(*x, **k), **kw)
    print('confirm', kw, '\n   same-spot max drift:', a, '\n   sim walks:', b)
