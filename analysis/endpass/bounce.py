import numpy as np
from refit import sweeps, echoes, roomfit, angd
def axis_profile(d, flt, rot, ax, half=25):
    acc = None; n = 0
    for f in d['frames']:
        if not flt(f) or not f.get('p'): continue
        n0 = rot + 90 * ax
        if min(abs(angd(f['h'], n0)), abs(angd(f['h'], n0 + 180))) < half:
            p = np.array((f['p'] + [-99] * 170)[:166], float); v = 10 ** (p / 10)
            acc = v if acc is None else acc + v; n += 1
    return (10 * np.log10(acc / n + 1e-30), n) if n else (None, 0)
def allround(d, flt):
    acc = None; n = 0
    for f in d['frames']:
        if not flt(f) or not f.get('p'): continue
        p = np.array((f['p'] + [-99] * 170)[:166], float); v = 10 ** (p / 10); acc = v if acc is None else acc + v; n += 1
    return 10 * np.log10(acc / n + 1e-30)
def peaks(mp, ref, lo=2.8, hi=4.95):
    out = []
    for i in range(int(lo / 0.03), min(len(mp) - 1, int(hi / 0.03))):
        if mp[i] >= mp[i - 1] and mp[i] > mp[i + 1]:
            loc = np.median(mp[max(0, i - 15):i + 16]); rel = mp[i] - ref[i]
            if mp[i] - loc >= 3: out.append((round(i * 0.03 + 0.015, 2), round(mp[i] - loc, 1), round(rel, 1)))
    return out
for lab, d, flt in sweeps():
    if 'knee' in lab: continue
    h, r, sf, t = echoes(d, flt); b = roomfit(h, r, sf)
    ar = allround(d, flt)
    for ax, nm in [(0, 'front-back'), (1, 'left-right')]:
        mp, n = axis_profile(d, flt, b['rot'], ax)
        if mp is None: continue
        S = b['D'][ax] + b['D'][ax + 2]
        print(f"{lab:12s} {nm:10s} box {S:.2f} | peaks 2.8-5 m (dist, dB over surroundings, dB over all-round): {peaks(mp, ar)}  ({n} readings)")
