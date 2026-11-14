"""Scan spot-2 slide direction (0.30 m) and facing; usage: scan_offset.py <analysis_dir> <map.npz>"""
import sys, numpy as np
sys.path.insert(0, sys.argv[1])
from combine_spots import sampler, hough, line_peaks
d = np.load(sys.argv[2]); g = d["grid"]
maps = [sampler(d["cross1"], g), sampler(d["cross2"], g)]
phis = np.arange(0, 360, 2.0); rhos = np.arange(0.35, 2.8, 0.01)
rows = []
for beta in (44.0, 0.0):
    for ang in range(0, 360, 15):   # slide direction, clockwise from phone-top-at-start
        a = np.deg2rad(ang); dx, dy = 0.30*np.sin(a), 0.30*np.cos(a)
        H, _ = hough(maps, g, [(0,0),(dx,dy)], [0, beta], phis, rhos)
        sm = line_peaks(H, phis, rhos)[1]
        rows.append((beta, ang, sm.max()/np.median(sm)))
for beta in (44.0, 0.0):
    r = [x for x in rows if x[0]==beta]; c = np.array([x[2] for x in r])
    best = r[int(np.argmax(c))]
    print(f"beta {beta:>4}: contrast min {c.min():.2f} median {np.median(c):.2f} max {c.max():.2f} (slide dir {best[1]} deg)  spread {(c.max()-np.median(c))/np.std(c):.1f} sd")
    print("   ", " ".join(f"{x[1]}:{x[2]:.2f}" for x in r))
