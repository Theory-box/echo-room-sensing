# End-of-scan refit prototype: replay the app's room fit on saved sweeps, then try hindsight fixes.
import json, numpy as np
import sys; L = (sys.argv[1] if len(sys.argv) > 1 else 'logs') + '/'  # folder holding the pulled sessions
RB_TOL, RB_FACE, RB_MIN, RB_MAX = 0.04, 30, 0.35, 5.0
BOUNCE_TOL, BOUNCE_MIN, BOUNCE_FRAC, RB_RINGN = 0.03, 10, 0.4, 3


def angd(a, b): return ((a - b + 180) % 360) - 180


def sumflag(r, rs):
    o = [v for v in rs if abs(v - r) > 0.005]
    for i in range(len(o)):
        if abs(2 * o[i] - r) < BOUNCE_TOL: return 1
        for k in range(i + 1, len(o)):
            if abs(o[i] + o[k] - r) < BOUNCE_TOL: return 1
    return 0


# the half-wall-room sweeps: (label, session, frame filter)
def sweeps():
    S = []
    def ld(s): return json.load(open(L + s + '/sonar_log.json'))
    d = ld('sweep-20261119-145617-963'); S.append(('Test1 head', d, lambda f: f.get('ts') == 1))
    S.append(('Test1 knee', d, lambda f: f.get('ts') == 3))
    d = ld('sweep-20261119-152557-632'); S.append(('Test2 head', d, lambda f: f.get('ts') == 1))
    S.append(('Test2 knee', d, lambda f: f.get('ts') == 3))
    d = ld('sweep-20261119-190859-643'); S.append(('Evening', d, lambda f: True))
    d = ld('sweep-20261119-193942-603')
    S.append(('Guided s1', d, lambda f: 77287 <= f['t'] < 119521))
    S.append(('Guided s2', d, lambda f: 119521 <= f['t'] < 160333))
    S.append(('Guided both', d, lambda f: 77287 <= f['t'] < 160333))
    return S


def echoes(d, flt, hkey='h'):
    H, R, SF, T = [], [], [], []
    for f in d['frames']:
        if not flt(f) or not f.get('e'): continue
        kept = [q for q in f['e'] if q[10] == 1 and q[0] > RB_MIN]
        rs = [q[0] for q in f['e']]
        for q in kept:
            H.append(f[hkey]); R.append(q[0] - (q[12] or 0) / 100); SF.append(sumflag(q[0], rs)); T.append(f['t'])
    return np.array(H), np.array(R), np.array(SF), np.array(T)


def ringfree(h, r):
    sc = np.floor((h % 360) / 30).astype(int)
    if len(set(sc)) < 10: return np.ones(len(h), bool), []
    b = np.round(r / 0.03).astype(int)
    cnt = {}
    for s, bb in zip(sc, b):
        for x in (bb - 1, bb, bb + 1): cnt[(x, s)] = cnt.get((x, s), 0) + 1
    ring = set()
    for x in set(b):
        if sum(1 for s in range(12) if cnt.get((x, s), 0) >= RB_RINGN) >= 9: ring.add(x)
    return np.array([x not in ring for x in b]), sorted(round(x * 0.03, 2) for x in ring)


def roomfit(h, r, sf, arm=0.25, rot_fixed=None, w=None, extra=None):
    keep, rings = ringfree(h, r)
    h, r, sf = h[keep], r[keep], sf[keep]
    wt = np.ones(len(h)) if w is None else w[keep]
    nb = int(round((RB_MAX - RB_MIN) / 0.01)); win = int(round(RB_TOL / 0.01))
    best = None
    rots = range(-45, 45) if rot_fixed is None else [rot_fixed]
    for rot in rots:
        D, votes, tot = [], [], 0
        for wl in range(4):
            nrm = rot + 90 * wl
            off = angd(h, nrm); m = np.abs(off) < RB_FACE
            dist = r[m] + arm * np.cos(np.radians(off[m]))
            bi = np.round((dist - RB_MIN) / 0.01).astype(int); ok = (bi >= 0) & (bi < nb)
            hist = np.bincount(bi[ok], weights=wt[m][ok], minlength=nb)[:nb]
            flg = np.bincount(bi[ok], weights=(sf[m][ok] * wt[m][ok]), minlength=nb)[:nb]
            c7 = np.convolve(hist, np.ones(7), 'same'); f7 = np.convolve(flg, np.ones(7), 'same')
            hist = np.where((c7 >= BOUNCE_MIN) & (f7 >= BOUNCE_FRAC * c7), 0, hist)
            run = np.convolve(hist, np.ones(2 * win + 1), 'same')
            if extra is not None: run = run + extra(wl, rot)
            bi = int(np.argmax(run)); D.append(RB_MIN + bi * 0.01); votes.append(run[bi]); tot += run[bi]
        if best is None or tot > best['tot']: best = dict(rot=rot, D=D, votes=votes, tot=tot)
    best['rings'] = rings
    return best


def fmt(f): return f"rot {f['rot']:4d}  D {' '.join(f'{x:.2f}' for x in f['D'])}  L {f['D'][0]+f['D'][2]:.2f} W {f['D'][1]+f['D'][3]:.2f}"


if __name__ == '__main__':
    for lab, d, flt in sweeps():
        h, r, sf, t = echoes(d, flt)
        logged = [f['rb'] for f in d['frames'] if flt(f) and 'rb' in f]
        f = roomfit(h, r, sf)
        print(f'{lab:12s} n={len(h):5d} replay {fmt(f)} | app last ' + (f"rot {logged[-1][0]} D {[round(x,2) for x in logged[-1][1:5]]}" if logged else '-'))
