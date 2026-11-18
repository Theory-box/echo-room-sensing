# Room-locked position tracking (offline prototype).
# Room frame: origin = where you stood when the box was fitted; heading frame = the app's (relative to Start).
# Box: wall j has outward normal n_j (unit, at heading rot + 90 j) and offset W_j (distance from the origin).
# You stand at p (2-D); the phone is ARM ahead along the heading u(theta). An echo from wall j at heading theta:
#   r = W_j - n_j . p - ARM*cos(theta - normal_j)   ->  measurement of n_j . p:  z = W_j - r - ARM*cos(off)
# Kalman filter on p (random walk, walking-speed process noise), one scalar update per echo matched to a wall
# (facing it within 30 deg, innovation within a gate).
import json, math, sys, importlib.util
import numpy as np
spec = importlib.util.spec_from_file_location('rf', 'roomfit.py'); rf = importlib.util.module_from_spec(spec); sys.argv = ['x', 'none']; spec.loader.exec_module(rf)
ARM = 0.25
def ad(a, b): return (a - b + 540) % 360 - 180
def detections(path):
    d = json.load(open(path)); fr = d['frames']; T0 = fr[0]['t']; out = []
    for x in fr:
        dets = [(e[0] - (e[12] / 100 if len(e) > 12 and e[12] is not None else 0)) for e in x['e'] if e[10] and e[0] > 0.35]
        out.append(((x['t'] - T0) / 1000, x['h'], dets, x))
    return d, out
def fit_box(rows, upto=None):
    h = []; r = []
    for t, th, dets, _ in rows:
        if upto is not None and t > upto: break
        for v in dets: h.append(th); r.append(v)
    p, score, votes = rf.fit_vote(np.array(h), np.array(r))
    return p[0], np.array(p[1:5]), votes, int(len(r) * 0.08 / 4)
class Tracker:
    def __init__(self, rot, W, sigma_r=0.02, q_walk=0.25, gate=0.08):
        self.rot, self.W = rot, W; self.p = np.zeros(2); self.P = np.eye(2) * 1e-4
        self.sr2 = sigma_r ** 2; self.q = q_walk ** 2; self.gate = gate; self.t = None; self.used = 0; self.rej = 0
        self.N = [np.array([math.sin(math.radians(rot + 90 * j)), math.cos(math.radians(rot + 90 * j))]) for j in range(4)]
    def step(self, t, theta, dets):
        if self.t is not None: self.P += np.eye(2) * self.q * max(0.0, t - self.t)
        self.t = t
        for r in dets:
            best = None
            for j in range(4):
                off = ad(theta, self.rot + 90 * j)
                if abs(off) >= 30: continue
                z = self.W[j] - r - ARM * math.cos(math.radians(off)); H = self.N[j]
                innov = z - H @ self.p; S = H @ self.P @ H + self.sr2
                if abs(innov) < self.gate + 2 * math.sqrt(S) and (best is None or abs(innov) < abs(best[0])): best = (innov, H, S)
            if best is None: self.rej += 1; continue
            innov, H, S = best; K = self.P @ H / S
            self.p = self.p + K * innov; self.P = self.P - np.outer(K, H) @ self.P; self.used += 1
        return self.p.copy()
if __name__ == '__main__':
    # 1) same-spot sweeps: fit the box on the first full turn, then track the rest -> p should stay near 0
    for s in ['161659-916', '161753-114', '161910-971', '140553-471', '121133-233']:
        d, rows = detections(f'logs/sweep-20261118-{s}-sonar_log.json')
        # time when 330 deg have been covered
        seen = set(); tlock = None
        for t, th, dets, _ in rows:
            seen.add(int((th % 360) // 30))
            if len(seen) >= 11: tlock = t; break
        if tlock is None: continue
        rot, W, votes, cl = fit_box(rows, tlock)
        tr = Tracker(rot, W); P = []
        for t, th, dets, _ in rows:
            if t <= tlock: continue
            P.append((t, *tr.step(t, th, dets)))
        P = np.array(P)
        print(f'{s} {d["settings"]["ping"]:11s}: box locked at {tlock:.0f} s ({min(W[0]+W[2],W[1]+W[3]):.2f} x {max(W[0]+W[2],W[1]+W[3]):.2f} m), then {P[-1,0]-tlock:.0f} s tracked: '
              f'position sd {100*P[:,1].std():.1f} / {100*P[:,2].std():.1f} cm, max drift {100*np.max(np.hypot(P[:,1],P[:,2])):.1f} cm, echoes used {tr.used} rejected {tr.rej}')
