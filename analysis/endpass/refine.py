import numpy as np, refit
from refit import sweeps, echoes, roomfit, angd
from absrot import offset, m90
def near_extra(D0, win=0.15):
    def ex(w, rot):
        x = refit.RB_MIN + np.arange(int(round((refit.RB_MAX - refit.RB_MIN) / 0.01))) * 0.01
        return np.where(np.abs(x - D0[w]) <= win, 0, -1e9)
    return ex
def refine(h, r, sf, base, tol=0.015, face=40, rng=25):
    refit.RB_TOL, refit.RB_FACE = tol, face
    best = None
    for rot in range(base['rot'] - rng, base['rot'] + rng + 1):
        # wall numbering may shift by a quarter turn: keep D0 matched to the walls by their direction
        f = roomfit(h, r, sf, rot_fixed=rot, extra=near_extra(base['D']))
        if best is None or f['tot'] > best['tot']: best = f
    refit.RB_TOL, refit.RB_FACE = 0.04, 30
    return best
if __name__ == '__main__':
    for lab, d, flt in sweeps():
        if 'knee' in lab: continue
        off, _ = offset(d, flt); h, r, sf, t = echoes(d, flt)
        b = roomfit(h, r, sf); f = refine(h, r, sf, b)
        print(f"{lab:12s} app-style: angle {m90(b['rot']+off)%90:5.1f}  {b['D'][0]+b['D'][2]:.2f} x {b['D'][1]+b['D'][3]:.2f}   refined: angle {m90(f['rot']+off)%90:5.1f}  {f['D'][0]+f['D'][2]:.2f} x {f['D'][1]+f['D'][3]:.2f}  D {[round(x,2) for x in f['D']]}")
    # guided final (greens) for reference
    print('Guided final (greens, rot -6): angle', (m90(-6 + 31.3)) % 90)
