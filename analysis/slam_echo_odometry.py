# Echo odometry: all echoes vote on how far you moved since the last reading; the room box then corrects.
# Between consecutive readings each echo is paired with the nearest echo of the previous reading (within ODO_PAIR).
# Every fixed thing ahead changes distance by about -(your step along the heading); things off to the side change less
# (cos of their angle), the floor/ceiling hardly at all. The biggest group of changes that agree (within ODO_AGREE)
# is taken as the step, if at least ODO_NEED echoes are in it. No step detector.
# The Kalman tracker of slam6 then uses this step as its prediction (the standing 5 cm gate is centred on where the
# odometry says you are now), and "moving" (recent odometry speed) replaces the walking flag for the wider gate.
import math, numpy as np
import slam5 as B, slam6 as C
S = B.S; ad = S.ad; ARM = S.ARM; M = B.M
class Odo:
    def __init__(self, pair=0.10, agree=0.015, need=2, maxstep=0.15):
        self.prev = None; self.pair, self.agree, self.need, self.maxstep = pair, agree, need, maxstep
    def step(self, dets):
        out = None
        if self.prev is not None and dets and self.prev:
            dl = []
            for r in dets:
                j = min(self.prev, key=lambda x: abs(x - r))
                if abs(j - r) < self.pair: dl.append(r - j)
            if len(dl) >= self.need:
                dl = np.array(dl); cnt = np.array([np.sum(np.abs(dl - c) < self.agree) for c in dl]); i = int(np.argmax(cnt))
                if cnt[i] >= self.need:
                    m = -float(np.mean(dl[np.abs(dl - dl[i]) < self.agree]))
                    if abs(m) <= self.maxstep: out = m
        self.prev = list(dets)
        return out          # metres moved along the heading (+ = forward), or None (no agreement)
class OdoTracker(C.T6):
    """Kalman on position: prediction = odometry step along the heading; correction = echoes vs the locked box."""
    def __init__(self, *a, vthr=0.08, vtau=1.0, odo_kw=None, use_odo=True, **k):
        super().__init__(*a, hold=1.0, agree=0.06, **k); self.odo = Odo(**(odo_kw or {})); self.v = 0.0
        self.vthr, self.vtau, self.use_odo = vthr, vtau, use_odo; self.tl = None
    def step(self, t, theta, dets, walking=None):
        dt = 0 if self.tl is None else max(1e-3, t - self.tl); self.tl = t
        m = self.odo.step(dets)
        if self.use_odo and m is not None:
            u = np.array([math.sin(math.radians(theta)), math.cos(math.radians(theta))])
            self.x[:2] = self.x[:2] + m * u
            self.P += np.outer(u, u) * (0.3 * abs(m) + 0.005) ** 2     # odometry is rough (off-axis echoes read short)
        sp = abs(m) / dt if m is not None else 0.0
        self.v += (1 - math.exp(-dt / self.vtau)) * (sp - self.v)
        moving = self.v > self.vthr
        return super().step(t, theta, dets, moving)
def walking_truth(fn, t): return np.linalg.norm(fn(t + 0.3)[0] - fn(t - 0.3)[0]) > 0.01
def sims(make, seeds=(5, 6, 7), floor=True):
    res = {}
    for sd in seeds:
        M.rng = np.random.default_rng(sd)
        for name, fn in M.FNS.items():
            rows = M.sim_rows(fn, 44)
            if floor:   # a floor/ceiling echo at a fixed distance, heard often
                rows = [(t, th, d + ([1.05 + M.rng.normal(0, 0.01)] if M.rng.random() < 0.5 else []), x) for t, th, d, x in rows]
            rot, W, votes, cl = S.fit_box(rows, 20)
            tr = make(rot, W, votes, cl); E = []
            for t, th, dets, _ in rows:
                p = tr.step(t, th, dets, walking_truth(fn, t))
                if t > 20: E.append(np.linalg.norm(p - fn(t)[0]))
            res.setdefault(name, []).extend(E)
    return ' | '.join(f'{n}: med {100*np.median(E):.0f} p90 {100*np.percentile(E,90):.0f}' for n, E in res.items()) + ' cm'
def same_spot(make, all_echoes=False):
    out = []
    for s in ['161659-916', '161753-114', '161910-971', '140553-471', '121133-233', '162000-283', '162107-513', '141954-224']:
        d, rows = S.detections(f'logs/sweep-20261118-{s}-sonar_log.json')
        if all_echoes: rows = [(t, th, [e[0] - (e[12] or 0) / 100 for e in x['e'] if e[0] > 0.35], x) for t, th, _, x in rows]
        seen = set(); tlock = None
        for t, th, dets, _ in rows:
            seen.add(int((th % 360) // 30))
            if len(seen) >= 11: tlock = t; break
        if tlock is None: continue
        rot, W, votes, cl = S.fit_box(rows, tlock)
        tr = make(rot, W, votes, cl); P = []
        for t, th, dets, _ in rows:
            if t <= tlock: continue
            P.append(tr.step(t, th, dets, False))
        P = np.array(P); out.append(f'{100*np.max(np.hypot(P[:,0],P[:,1])):.0f}')
    return ' '.join(out) + ' cm'
if __name__ == '__main__':
    import slam7
    M.FNS['walk + sweep 90'] = slam7.walk_d
    class NoWalk(C.T6):          # today's app when walking isn't detected
        def step(self, t, th, d, w=None): return super().step(t, th, d, False)
    class Oracle(C.T6):          # today's app with a perfect step detector
        pass
    cands = {
        'current tracker, walking never detected (what happened)': lambda *a: NoWalk(*a, hold=1.0, agree=0.06),
        'current tracker + perfect step detector': lambda *a: Oracle(*a, hold=1.0, agree=0.06),
        'echo odometry + box': lambda *a: OdoTracker(*a),
        'echo odometry + box, need 3 agreeing': lambda *a: OdoTracker(*a, odo_kw=dict(need=3)),
        'echo odometry + box, agree 2.5 cm': lambda *a: OdoTracker(*a, odo_kw=dict(agree=0.025)),
    }
    for name, mk in cands.items():
        print(name, flush=True)
        print('   sim walks:', sims(mk), flush=True)
        print('   same-spot max drift (confirmed echoes):', same_spot(mk), flush=True)
        if 'odometry' in name: print('   same-spot max drift (all echoes):', same_spot(mk, True), flush=True)
