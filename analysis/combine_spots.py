"""Combine per-spot back-projection maps into wall-line estimates (Hough voting).

A flat wall returns its specular echo along its normal: from a spot at c, the wall
{x : n(phi).x = rho} appears at distance r = rho - n.c in direction phi. Each spot's map is
sampled at that point; walls consistent across spots score high in (phi, rho) space.

usage: python combine_spots.py <map.npz> <png> <spot2_dx> <spot2_dy> <beta_list_deg>
  spot2 offset in the spot-1 start frame (x right, y toward the phone's top at stop 1);
  beta = spot-2 frame rotation relative to spot 1 (deg, clockwise positive), comma-separated to compare.
"""
import json
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy import ndimage


def sampler(m, g):
    step = g[1] - g[0]
    sm = ndimage.gaussian_filter(m, 1.0)
    sm = sm / (np.median(sm[sm > 0]) + 1e-12)

    def f(x, y):
        return ndimage.map_coordinates(sm, [(y - g[0]) / step, (x - g[0]) / step], order=1, mode="constant")
    return f


def hough(maps, g, centres, betas, phis, rhos, rmin=0.35):
    P, R = np.meshgrid(np.deg2rad(phis), rhos, indexing="ij")
    nx, ny = np.sin(P), np.cos(P)            # bearing phi measured clockwise from +y (phone top at start)
    acc = []
    for f, c, b in zip(maps, centres, betas):
        r = R - (nx * c[0] + ny * c[1])
        # direction phi in the spot frame: rotate by -beta (spot frame turned clockwise by beta)
        pl = P - np.deg2rad(b)
        x, y = r * np.sin(pl), r * np.cos(pl)
        v = f(x.ravel(), y.ravel()).reshape(r.shape)
        v[(r < rmin) | (r > g[-1])] = 0
        acc.append(v)
    acc = np.array(acc)
    return np.sqrt(np.prod(np.clip(acc, 0, None), axis=0)) if len(acc) == 2 else acc.mean(0), acc


def line_peaks(H, phis, rhos, n=6):
    sm = ndimage.gaussian_filter(H, (1.5, 1.5))
    mx = ndimage.maximum_filter(sm, size=(15, 25), mode="wrap")
    ii, jj = np.nonzero(sm == mx)
    order = np.argsort(sm[ii, jj])[::-1][:n]
    top = sm[ii[order[0]], jj[order[0]]]
    return [{"bearing_deg": int(phis[ii[k]]), "dist_m": round(float(rhos[jj[k]]), 2),
             "strength": round(float(sm[ii[k], jj[k]] / top), 2)} for k in order], sm


def main(npz, png, dx, dy, beta_list):
    d = np.load(npz)
    g = d["grid"]
    maps = [sampler(d["cross1"], g), sampler(d["cross2"], g)]
    phis = np.arange(0, 360, 2.0)
    rhos = np.arange(0.35, 2.8, 0.01)
    results = {}
    fig, axs = plt.subplots(1, len(beta_list), figsize=(6.2 * len(beta_list), 6.6), squeeze=False)
    for ax, beta in zip(axs[0], beta_list):
        H, _ = hough(maps, g, [(0, 0), (dx, dy)], [0, beta], phis, rhos)
        pk, sm = line_peaks(H, phis, rhos)
        # contrast: how much the best line stands out from the typical line hypothesis
        contrast = float(sm.max() / (np.median(sm) + 1e-12))
        results[beta] = {"contrast": round(contrast, 2), "walls": pk}
        ax.set_facecolor("#111")
        for r in (1, 2):
            ax.add_patch(plt.Circle((0, 0), r, fill=False, color="w", lw=0.5, alpha=0.3, ls="--"))
        for k, p in enumerate(pk, 1):
            ph = np.deg2rad(p["bearing_deg"])
            n = np.array([np.sin(ph), np.cos(ph)])
            foot = n * p["dist_m"]
            t = np.array([n[1], -n[0]])
            a, b = foot - 1.2 * t, foot + 1.2 * t
            ax.plot([a[0], b[0]], [a[1], b[1]], color="#ffb300", lw=1 + 3 * p["strength"], alpha=0.4 + 0.6 * p["strength"])
            ax.text(foot[0] * 1.08, foot[1] * 1.08, f"{k}: {p['dist_m']} m", color="#ffb300", fontsize=9)
        for (cx, cy), lab, col in (((0, 0), "spot 1", "#4fc3f7"), ((dx, dy), "spot 2", "#81c784")):
            ax.plot(cx, cy, "s", color=col, ms=7)
            ax.text(cx + 0.05, cy - 0.18, lab, color=col, fontsize=8)
        ax.annotate("", xy=(0, 0.45), xytext=(0, 0.08), arrowprops=dict(arrowstyle="->", color="#4fc3f7", lw=2))
        ax.text(-0.55, 0.5, "phone top\nat start", color="#4fc3f7", fontsize=8)
        ax.set_xlim(-3, 3)
        ax.set_ylim(-3, 3)
        ax.set_aspect("equal")
        ax.set_title(f"Wall candidates, spot-2 facing offset {beta}° (contrast {contrast:.2f})", fontsize=10)
        ax.set_xlabel("m (right of start)")
        ax.set_ylabel("m (ahead of phone top at start)")
    fig.tight_layout()
    fig.savefig(png, dpi=105)
    print(json.dumps(results, indent=1))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], float(sys.argv[3]), float(sys.argv[4]),
         [float(b) for b in sys.argv[5].split(",")])
