# Per wall: an echo from a flat wall, heard while you turn on the spot, follows r(h) = D - a*cos(h - n):
# the phone swings on your arm (a), nearest when facing the wall square (h = n). Fit D, a, n per wall from all its echoes.
import numpy as np, sys
from refit import sweeps, echoes, roomfit, angd, fmt
def wallcurve(h, r, rot, D, arm=0.25, span=45, gate=0.06):
    out = []
    for w in range(4):
        n0 = rot + 90 * w; a, n, Dw = arm, n0, D[w]
        for it in range(4):
            off = angd(h, n); m = (np.abs(off) < span) & (np.abs(r - (Dw - a * np.cos(np.radians(off)))) < gate)
            if m.sum() < 15: break
            th = np.radians(h[m]); A = np.c_[np.ones(m.sum()), np.cos(th), np.sin(th)]
            (c0, p, q), *_ = np.linalg.lstsq(A, r[m], rcond=None)
            a2 = np.hypot(p, q); n2 = np.degrees(np.arctan2(-q, -p))
            if a2 > 0.9: break
            a, n, Dw = a2, n2, c0
        res = r[m] - (Dw - a * np.cos(np.radians(angd(h[m], n)))) if m.sum() >= 15 else None
        hs = angd(h[m], n0) if m.sum() >= 15 else None
        out.append(dict(w=w, n=int(m.sum()), D=Dw, a=a, nrm=angd(n, n0) + n0, res=None if res is None else res.std(),
                        hspan=None if hs is None else (hs.min(), hs.max())))
    return out
for lab, d, flt in sweeps():
    if 'knee' in lab: continue
    h, r, sf, t = echoes(d, flt); f = roomfit(h, r, sf)
    print('==', lab, fmt(f))
    for c in wallcurve(h, r, f['rot'], f['D']):
        if c['res'] is None: print(f"   wall {c['w']}: too few echoes on its curve ({c['n']})"); continue
        print(f"   wall {c['w']}: {c['n']:4d} echoes  D {c['D']+c['a']:.2f} (axis) arm {c['a']*100:4.0f} cm  normal {c['nrm']:6.1f} (box {f['rot']+90*c['w']})  fit spread {c['res']*100:.1f} cm  headings {c['hspan'][0]:.0f}..{c['hspan'][1]:.0f}")
