"""Fit vertical walls to an Echo Room sweep with an image-source (mirror) model.

For a candidate wall (unit normal at bearing phi, distance rho from the session origin), every stop k
and mic i predicts an exact echo delay: |S'_k - M_ik| where S'_k is the speaker mirrored in the wall.
That uses both the inter-mic delay and each mic's range swing as the phone rotates. Score = sum of IR
envelopes at the predicted delays. Per-distance contrast (subtract the median over bearings) removes
rotation-invariant energy (ceiling/floor rings). Optional right-angle (Manhattan) constraint: four walls
at phi0 + 0/90/180/270.

usage: python fit_walls.py <session_dir> <out_prefix> [--offsets "0,0;0.3,0"] [--flip-yaw] [--mirror-x]
                           [--spots 1,2] [--rmax 4]
"""
import argparse
import json
import os
import sys

import numpy as np
from scipy import ndimage
from scipy.io import wavfile

sys.path.insert(0, os.path.dirname(__file__))
from sweep_map import C, M as MICS, S as SPK, UP, impulse_responses, log_sweep  # noqa: E402


def rot(alpha_deg):
    a = np.deg2rad(alpha_deg)
    return np.array([[np.cos(a), np.sin(a)], [-np.sin(a), np.cos(a)]])


def load(sess, spots=None):
    man = json.load(open(os.path.join(sess, "session.json"), encoding="utf-8"))
    sr = man["plan"]["sr"]
    sw = man["plan"]["sweep"]
    sweep = log_sweep(sr, sw["f1"], sw["f2"], sw["T"])
    caps = [c for c in man["captures"] if spots is None or c["spot"] in spots]
    out = []
    for c in caps:
        _, x = wavfile.read(os.path.join(sess, c["file"].split("/")[-1]))
        irs, direct = impulse_responses(x.astype(np.float64), sweep, sr, ir_len=0.03)
        out.append([c, irs, direct])
    med = float(np.median([d[1] - d[0] for _, _, d in out]))
    for _, irs, direct in out:
        lo, hi = int(direct[0] + med - 2 * UP), int(direct[0] + med + 2 * UP) + 1
        env = np.abs(irs[1][max(lo, 0):hi])
        direct[1] = max(lo, 0) + float(np.argmax(env)) if len(env) else direct[0] + med
    # Session yaw: v2 files store it; legacy (v1) files are per spot, and spot n started where spot n-1 ended.
    last_end = 0.0
    for spot in sorted({c["spot"] for c, _, _ in out}):
        rows = [r for r in out if r[0]["spot"] == spot]
        for r in rows:
            c = r[0]
            if "yawSessionDeg" in c:
                r.append(float(c["yawSessionDeg"]))
            else:
                rel = (c["turnDir"] * c["yawStartDeg"]) if c["turnDir"] else 0.0
                if c["stop"] > 1 and not c["turnDir"]:
                    rel = -c["yawStartDeg"]
                r.append(last_end + rel)
        if "yawSessionDeg" not in rows[0][0]:
            last_end = rows[-1][3]
    return man, sr, out, med / UP


def envelopes(irs, direct, sr):
    fs = sr * UP
    env = []
    for i in range(2):
        e = np.abs(irs[i])
        tail = e[int(direct[i] + 0.004 * fs):]
        e = e / (np.median(tail) + 1e-12)
        env.append(e)
    return env


def score(data, sr, offsets, phis, rhos, flip=False, mirror=False):
    fs = sr * UP
    P, R = np.meshgrid(np.deg2rad(phis), rhos, indexing="ij")
    N = np.stack([np.sin(P), np.cos(P)], -1)                 # wall normal, bearing clockwise from +y
    mics = MICS * ([-1, 1] if mirror else [1, 1])
    spk = SPK * ([-1, 1] if mirror else [1, 1])
    H = np.zeros(P.shape)
    for c, irs, direct, yaw in data:
        Rk = rot(-yaw if flip else yaw)
        centre = np.asarray(offsets.get(c["spot"], (0.0, 0.0)))
        S = centre + Rk @ spk
        env = envelopes(irs, direct, sr)
        Sd = R - (N @ S)                                     # signed distance speaker -> wall
        Sp = S + 2 * Sd[..., None] * N                       # mirrored speaker
        for i in range(2):
            Mw = centre + Rk @ mics[i]
            L = np.linalg.norm(Sp - Mw, axis=-1)
            d0 = np.linalg.norm(Mw - S)
            idx = direct[i] + (L - d0) / C * fs
            v = ndimage.map_coordinates(env[i], [idx.ravel()], order=1, mode="constant").reshape(idx.shape)
            H += v * L
    return H


def manhattan(Hc, phis, rhos, ncand=6, corner_w=1.0):
    """Rectangle fit: orientation phi0 + four wall distances. Each candidate rectangle predicts 4 wall echoes
    and 4 corner echoes (a corner returns sound like a retroreflector, at the corner's bearing/distance);
    the score is the evidence at all 8. Candidate distances per direction = local maxima along rho."""
    dr = rhos[1] - rhos[0]
    pos = np.clip(Hc, 0, None)

    def at(phi_deg, r):
        return float(ndimage.map_coordinates(pos, [[phi_deg % 360], [(r - rhos[0]) / dr]], order=1, mode="constant")[0])

    best, per_p0 = None, []
    for p0 in range(0, 90):
        cands = []
        for j in range(4):
            col = ndimage.gaussian_filter1d(pos[(p0 + 90 * j) % 360], 2)
            pk = np.nonzero((col > np.roll(col, 1)) & (col >= np.roll(col, -1)))[0]
            pk = pk[np.argsort(col[pk])[::-1][:ncand]]
            cands.append([(float(rhos[k]), float(col[k])) for k in pk] or [(float(rhos[0]), 0.0)])
        bp = None
        for d0 in cands[0]:
            for d1 in cands[1]:
                for d2 in cands[2]:
                    for d3 in cands[3]:
                        ds = [d0[0], d1[0], d2[0], d3[0]]
                        s = d0[1] + d1[1] + d2[1] + d3[1]
                        for j in range(4):
                            a, b = np.deg2rad(p0 + 90 * j), np.deg2rad(p0 + 90 * (j + 1))
                            v = ds[j] * np.array([np.sin(a), np.cos(a)]) + ds[(j + 1) % 4] * np.array([np.sin(b), np.cos(b)])
                            s += corner_w * at(np.degrees(np.arctan2(v[0], v[1])), float(np.hypot(*v)))
                        if bp is None or s > bp[0]:
                            bp = (s, ds, [d0[1], d1[1], d2[1], d3[1]])
        per_p0.append(bp[0])
        if best is None or bp[0] > best[0]:
            best = (bp[0], p0, bp[1], bp[2])
    return best, np.array(per_p0)


def free_peaks(Hc, phis, rhos, n=6):
    sm = ndimage.gaussian_filter(Hc, (2, 2), mode=("wrap", "nearest"))
    mx = ndimage.maximum_filter(sm, size=(21, 41), mode=("wrap", "nearest"))
    ii, jj = np.nonzero((sm == mx) & (sm > 0))
    o = np.argsort(sm[ii, jj])[::-1][:n]
    top = sm[ii[o[0]], jj[o[0]]]
    return [{"bearing_deg": int(phis[ii[k]]), "dist_m": round(float(rhos[jj[k]]), 2),
             "rel": round(float(sm[ii[k], jj[k]] / top), 2)} for k in o]


def run(sess, prefix, offsets, flip=False, mirror=False, spots=None, rmax=5.0, plot=True):
    man, sr, data, med = load(sess, spots)
    phis = np.arange(0, 360, 1.0)
    rhos = np.arange(0.3, rmax, 0.005)
    H = score(data, sr, offsets, phis, rhos, flip, mirror)
    iso = np.median(H, axis=0)
    Hc = ndimage.gaussian_filter1d(H - iso[None, :], 1.5, axis=1)
    (s, p0, dists, strengths), allp = manhattan(Hc, phis, rhos)
    sharp = float((allp.max() - np.median(allp)) / (np.std(allp) + 1e-12))
    res = {"session": man.get("version"), "direct_offset_samples": round(med, 2), "flip_yaw": flip, "mirror_x": mirror,
           "manhattan": {"score": round(float(s), 1), "phi0_deg": p0, "walls": [{"bearing_deg": (p0 + 90 * j) % 360, "dist_m": round(d, 3),
                                                     "strength": round(st, 1)} for j, (d, st) in enumerate(zip(dists, strengths))],
                         "room_size_m": [round(dists[0] + dists[2], 2), round(dists[1] + dists[3], 2)],
                         "orientation_sharpness_sd": round(sharp, 2)},
           "free_peaks": free_peaks(Hc, phis, rhos),
           "isotropic_peaks_m": [round(float(rhos[k]), 2) for k in np.argsort(ndimage.gaussian_filter1d(iso, 2))[::-1][:40]
                                 if True][:1]}
    if "truth" in man:
        res["truth"] = man["truth"]
    if plot:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(1, 2, figsize=(12.5, 5.6))
        ax[0].imshow(Hc.T, origin="lower", aspect="auto", extent=[phis[0], phis[-1], rhos[0], rhos[-1]], cmap="magma",
                     vmin=0, vmax=np.percentile(Hc, 99.8))
        for j in range(4):
            ax[0].plot((p0 + 90 * j) % 360, dists[j], "o", mfc="none", mec="#7CFC00", ms=12, mew=2)
        if "truth" in man:
            for w in man["truth"]["walls"]:
                ax[0].plot(w["bearing_deg"], w["dist_m"], "x", color="cyan", ms=10, mew=2)
        ax[0].set_xlabel("wall direction (deg clockwise from phone top at start)")
        ax[0].set_ylabel("wall distance (m)")
        ax[0].set_title("Wall evidence (green = right-angle fit" + (", cyan = true walls)" if "truth" in man else ")"))
        a = ax[1]
        a.set_facecolor("#111")
        for j in range(4):
            ph = np.deg2rad((p0 + 90 * j) % 360); n = np.array([np.sin(ph), np.cos(ph)]); t = np.array([n[1], -n[0]])
            f = n * dists[j]
            a.plot(*np.array([f - 4 * t, f + 4 * t]).T, color="#ffb300", lw=2.5)
            a.text(*(f * 1.05), f"{dists[j]:.2f} m", color="#ffb300", fontsize=9)
        if "truth" in man:
            for w in man["truth"]["walls"]:
                ph = np.deg2rad(w["bearing_deg"]); n = np.array([np.sin(ph), np.cos(ph)]); t = np.array([n[1], -n[0]])
                f = n * w["dist_m"]; a.plot(*np.array([f - 4 * t, f + 4 * t]).T, color="cyan", lw=1, ls="--")
        for sp, off in offsets.items():
            a.plot(*off, "s", color="#4fc3f7", ms=6)
        a.annotate("", xy=(0, 0.5), xytext=(0, 0.08), arrowprops=dict(arrowstyle="->", color="#4fc3f7", lw=2))
        a.set_xlim(-3.5, 3.5); a.set_ylim(-3.5, 3.5); a.set_aspect("equal")
        a.set_title(f"Right-angle wall fit (orientation sharpness {sharp:.1f} SD)" + (" vs truth (dashed)" if "truth" in man else ""))
        fig.tight_layout(); fig.savefig(prefix + ".png", dpi=100)
    json.dump(res, open(prefix + ".json", "w"), indent=1)
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sess"); ap.add_argument("prefix")
    ap.add_argument("--offsets", default="0,0")
    ap.add_argument("--flip-yaw", action="store_true"); ap.add_argument("--mirror-x", action="store_true")
    ap.add_argument("--spots", default=None); ap.add_argument("--rmax", type=float, default=5.0)
    a = ap.parse_args()
    offs = {i + 1: tuple(map(float, s.split(","))) for i, s in enumerate(a.offsets.split(";"))}
    spots = [int(s) for s in a.spots.split(",")] if a.spots else None
    r = run(a.sess, a.prefix, offs, a.flip_yaw, a.mirror_x, spots, a.rmax)
    m = r["manhattan"]
    print(json.dumps({"score": m["score"], "phi0": m["phi0_deg"], "walls": [(w["bearing_deg"], w["dist_m"]) for w in m["walls"]],
                      "room": m["room_size_m"], "sharp_sd": m["orientation_sharpness_sd"],
                      "truth": [(w["bearing_deg"], w["dist_m"]) for w in r.get("truth", {}).get("walls", [])]}))


if __name__ == "__main__":
    main()
