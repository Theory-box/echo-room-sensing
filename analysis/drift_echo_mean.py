# Heading drift from the room: a flat wall is heard symmetrically around its perpendicular, so the average
# (heading - wall normal) over echoes from that wall is ~0 -- unless the gyro heading has drifted, then it equals the
# drift. Online estimate (as the app would do it): box locked after the first full turn; then every echo within 5 cm of
# a locked wall's distance and within 35 deg of its normal adds (heading - normal) to a running mean (time constant TAU);
# corrected heading = heading - drift estimate. The locked box is then refitted from the corrected echoes.
# Test (no ground truth for the true heading): does the correction make the whole session's echoes agree better with
# ONE box? Score = echoes explained by the best box (fit_vote total) with raw vs corrected headings, and the box
# rotation fitted on the first vs last minute (should match if headings are consistent).
import json, math, sys, numpy as np, importlib.util
sys.argv = ['x', 'none']
spec = importlib.util.spec_from_file_location('rf', 'roomfit.py'); rf = importlib.util.module_from_spec(spec); spec.loader.exec_module(rf)
ARM = 0.25
def ad(a, b): return (a - b + 540) % 360 - 180
def echoes(fr):
    T0 = fr[0]['t']; out = []
    for x in fr:
        rs = [e[0] - (e[12] or 0) / 100 for e in x['e'] if len(e) > 12 and e[10] and e[0] > 0.35]
        out.append(((x['t'] - T0) / 1000, x['h'], rs))
    return out
def fit(rows, corr=None, t0=0, t1=1e9):
    h = []; r = []
    for k, (t, th, rs) in enumerate(rows):
        if t < t0 or t >= t1: continue
        hc = th - (corr[k] if corr is not None else 0)
        for v in rs: h.append(hc); r.append(v)
    if len(r) < 60: return None
    return rf.fit_vote(np.array(h), np.array(r))
def online(rows, tau=20.0, face=35, tol=0.05):
    seen = set(); lock = None; est = 0.0; corr = []; tl = None; tr = []
    for k, (t, th, rs) in enumerate(rows):
        if lock is None:
            seen.add(int((th % 360) // 30))
            if len(seen) >= 11:
                p, sc, v = fit(rows[:k + 1]); lock = (p[0], p[1:5]); tl = t
            corr.append(0.0); continue
        hc = th - est; rot, D = lock; offs = []
        for j in range(4):
            off = ad(hc, rot + 90 * j)
            if abs(off) >= face: continue
            pred = D[j] - ARM * math.cos(math.radians(off))
            offs += [off for v in rs if abs(v - pred) < tol]
        for off in offs:
            est += (1 - math.exp(-1 / (tau * 3))) * off     # ~3 matched echoes per second -> time constant ~tau s
        corr.append(est); tr.append((t, est))
    return corr, tl, tr
if __name__ == '__main__':
    for s in ['184525-732', '184843-704', '185155-137', '185319-472', '185606-164', '173253-126', '121133-233', '161659-916', '140553-471']:
        d = json.load(open(f'logs/sweep-20261118-{s}-sonar_log.json')); rows = echoes(d['frames'])
        corr, tl, tr = online(rows)
        if tl is None: continue
        T = rows[-1][0]
        raw = fit(rows); cor = fit(rows, corr)
        a0 = fit(rows, None, 0, 60); a1 = fit(rows, None, T - 60, T); b1 = fit(rows, corr, T - 60, T)
        trs = ' '.join(f'{v:+.0f}' for t, v in tr[::max(1, len(tr) // 10)])
        print(f"{s} {d['settings']['ping'][:10]:10s} {T:.0f}s | echoes explained by one box: raw {raw[1]} -> corrected {cor[1]} ({100*(cor[1]-raw[1])/raw[1]:+.1f}%) | "
              f"box rotation first minute {a0[0][0] if a0 else '-'}, last minute raw {a1[0][0] if a1 else '-'} / corrected {b1[0][0] if b1 else '-'} | drift estimate over time: {trs}")
