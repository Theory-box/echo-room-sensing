# Tracker with a walking flag (from the phone's step detector in the app; known in the sim):
# standing -> fixed 5 cm gate, tiny process noise (steady); walking -> gate grows with time since that axis was last
# confirmed (walking speed allowance), larger process noise. Optional velocity state (constant-velocity model).
import sys, math, numpy as np
import slam4 as M
S = M.S; ad = S.ad; ARM = S.ARM
class T5:
    def __init__(self, rot, W, votes=None, cl=0, sr=0.02, q_stand=0.02, q_walk=0.4, gate=0.05, vmax=0.7, gmax=0.8, vel=False):
        self.rot, self.W = rot, W; self.ok = [True] * 4 if votes is None else [v > 2 * cl for v in votes]
        self.N = [np.array([math.sin(math.radians(rot + 90 * j)), math.cos(math.radians(rot + 90 * j))]) for j in range(4)]
        self.vel = vel; n = 4 if vel else 2; self.x = np.zeros(n); self.P = np.eye(n) * 1e-4
        if vel: self.P[2:, 2:] = np.eye(2) * 0.01
        self.sr2 = sr * sr; self.qs, self.qw = q_stand ** 2, q_walk ** 2; self.gate, self.vmax, self.gmax = gate, vmax, gmax
        self.t = None; self.lastax = [0.0, 0.0]; self.used = self.rej = 0
    @property
    def p(self): return self.x[:2]
    def step(self, t, theta, dets, walking):
        dt = 0 if self.t is None else max(0.0, t - self.t); self.t = t
        if self.vel:
            F = np.eye(4); F[0, 2] = F[1, 3] = dt
            if not walking: self.x[2:] *= math.exp(-dt / 0.3)          # standing: velocity dies out fast
            self.x = F @ self.x; Q = np.zeros((4, 4)); Q[2:, 2:] = np.eye(2) * (self.qw if walking else self.qs) * dt * 4
            Q[:2, :2] = np.eye(2) * self.qs * dt; self.P = F @ self.P @ F.T + Q
        else:
            self.P += np.eye(2) * (self.qw if walking else self.qs) * dt
        for r in dets:
            best = None
            for j in range(4):
                if not self.ok[j]: continue
                off = ad(theta, self.rot + 90 * j)
                if abs(off) >= 30: continue
                z = self.W[j] - r - ARM * math.cos(math.radians(off)); a = j % 2; v = z if j < 2 else -z
                H = np.zeros(len(self.x)); H[:2] = self.N[a]
                g = self.gate + (min(self.gmax, self.vmax * (t - self.lastax[a])) if walking else 0)
                innov = v - H @ self.x
                if abs(innov) < g and (best is None or abs(innov) < abs(best[0])): best = (innov, H, a)
            if best is None: self.rej += 1; continue
            innov, H, a = best; Sv = H @ self.P @ H + self.sr2; K = self.P @ H / Sv
            self.x = self.x + K * innov; self.P = self.P - np.outer(K, H) @ self.P; self.used += 1; self.lastax[a] = t
        return self.x[:2].copy()
def same_spot(**kw):
    out = []
    for s in ['161659-916', '161753-114', '161910-971', '140553-471', '121133-233']:
        d, rows = S.detections(f'logs/sweep-20261118-{s}-sonar_log.json')
        seen = set(); tlock = None
        for t, th, dets, _ in rows:
            seen.add(int((th % 360) // 30))
            if len(seen) >= 11: tlock = t; break
        rot, W, votes, cl = S.fit_box(rows, tlock)
        tr = T5(rot, W, votes, cl, **kw); P = []
        for t, th, dets, _ in rows:
            if t <= tlock: continue
            P.append(tr.step(t, th, dets, False))
        P = np.array(P); out.append(f'{100*np.max(np.hypot(P[:,0],P[:,1])):.0f}')
    return ' '.join(out) + ' cm'
def sims(seeds=(5, 6, 7), **kw):
    res = {}
    for sd in seeds:
        M.rng = np.random.default_rng(sd)
        for name, fn in M.FNS.items():
            rows = M.sim_rows(fn, 44)
            rot, W, votes, cl = S.fit_box(rows, 20)
            tr = T5(rot, W, votes, cl, **kw); E = []
            for t, th, dets, _ in rows:
                truth = fn(t)[0]; walking = np.linalg.norm(fn(t + 0.3)[0] - fn(t - 0.3)[0]) > 0.01   # step detector stand-in
                p = tr.step(t, th, dets, walking)
                if t > 20: E.append(np.linalg.norm(p - truth))
            res.setdefault(name, []).extend(E)
    return ' | '.join(f'{n}: med {100*np.median(E):.0f} p90 {100*np.percentile(E,90):.0f}' for n, E in res.items()) + ' cm'
if __name__ == '__main__':
    for kw in (dict(), dict(vel=True), dict(vmax=1.0), dict(vel=True, vmax=1.0), dict(q_walk=0.8), dict(vel=True, q_walk=0.8, vmax=1.0)):
        print(kw, '\n   same-spot max drift:', same_spot(**kw), '\n   sim walks:', sims(**kw))
