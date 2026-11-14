"""Plot the back-projected reflector maps from sweep_map.py and list the strongest peaks.

usage: python plot_map.py <out_prefix> <png>
"""
import json
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy import ndimage


def clock(bearing_deg):
    """Bearing clockwise from the phone's top at the first stop -> clock position."""
    h = round((bearing_deg % 360) / 30) % 12
    return 12 if h == 0 else h


def peaks(m, g, n=8, min_sep=0.25):
    sm = ndimage.gaussian_filter(m, 2)
    step = g[1] - g[0]
    mx = ndimage.maximum_filter(sm, size=int(min_sep / step))
    ys, xs = np.nonzero((sm == mx) & (sm > 0))
    order = np.argsort(sm[ys, xs])[::-1][:n]
    top = sm[ys[order[0]], xs[order[0]]] if len(order) else 1
    out = []
    for i in order:
        x, y = g[xs[i]], g[ys[i]]
        b = np.degrees(np.arctan2(x, y)) % 360
        out.append({"x": round(float(x), 2), "y": round(float(y), 2), "dist_m": round(float(np.hypot(x, y)), 2),
                    "bearing_deg": round(float(b)), "clock": clock(b), "strength": round(float(sm[ys[i], xs[i]] / top), 2)})
    return out


def main(prefix, png):
    d = np.load(prefix + ".npz")
    g = d["grid"]
    spots = sorted(int(k[5:]) for k in d.files if k.startswith("cross"))
    fig, axs = plt.subplots(1, len(spots), figsize=(6 * len(spots), 6.4), squeeze=False)
    report = {}
    for ax, s in zip(axs[0], spots):
        m = d[f"cross{s}"]
        # Contrast per distance: divide each 5 cm ring by its mean over all directions, so the map shows
        # which direction is brightest at each range (isotropic rings, e.g. ceiling/floor, go flat).
        X, Y = np.meshgrid(g, g)
        rb = np.round(np.hypot(X, Y) / 0.05).astype(int)
        ring_mean = ndimage.mean(m, labels=rb, index=np.arange(rb.max() + 1))
        m = m / (ring_mean[rb] + 1e-12)
        m[np.hypot(X, Y) > g[-1]] = 0
        m = ndimage.gaussian_filter(m, 1.5)
        m = np.clip(m - 1, 0, None)
        img = m / (np.percentile(m[m > 0], 99.5) + 1e-12)
        ext = [g[0], g[-1], g[0], g[-1]]
        ax.imshow(img, origin="lower", extent=ext, cmap="magma", vmin=0.05, vmax=0.9)
        for r in (1, 2, 3):
            ax.add_patch(plt.Circle((0, 0), r, fill=False, color="w", lw=0.6, alpha=0.35, ls="--"))
            ax.text(0.05, r + 0.04, f"{r} m", color="w", alpha=0.6, fontsize=8)
        ax.add_patch(plt.Rectangle((-0.035, -0.075), 0.07, 0.15, color="#4fc3f7"))
        ax.annotate("", xy=(0, 0.45), xytext=(0, 0.1), arrowprops=dict(arrowstyle="->", color="#4fc3f7", lw=2))
        ax.text(0.06, 0.35, "phone top\n(start)", color="#4fc3f7", fontsize=8)
        pk = peaks(m, g)
        for i, p in enumerate(pk, 1):
            ax.plot(p["x"], p["y"], "o", mfc="none", mec="#7CFC00", ms=11, mew=1.5)
            ax.text(p["x"] + 0.08, p["y"] + 0.08, str(i), color="#7CFC00", fontsize=10, weight="bold")
        ax.set_title(f"Spot {s}: echo sources seen from above")
        ax.set_xlabel("m (right of start)")
        ax.set_ylabel("m (ahead of phone top at start)")
        ax.set_aspect("equal")
        report[s] = pk
    fig.tight_layout()
    fig.savefig(png, dpi=110)
    print(json.dumps(report, indent=1))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
