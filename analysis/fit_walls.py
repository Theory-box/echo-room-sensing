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
from simulate import lin_chirp  # noqa: E402
from scipy import signal  # noqa: E402


def chirp_irs(x, sweep, sr, plan, which, band=(1000.0, 16000.0), ir_len=0.03):
    """IRs from one speaker's chirps only (plan.chirpA[which], 'L' or 'R'), averaged over its chirps.
    Located via the sweep (both speakers), so the timeline matches impulse_responses()."""
    mix = x.sum(axis=1)
    c = signal.fftconvolve(mix[: int(2.5 * sr)], sweep[::-1], mode="valid")
    base = int(np.argmax(np.abs(c))) - plan["sweep"]["start"]          # recording index of playback sample 0
    ca = plan["chirpA"]
    ch = lin_chirp(ca["f0"], ca["f1"], ca["T"], "tukey")
    pre, win = int(0.002 * sr), int(0.15 * sr)
    N = 1 << int(np.ceil(np.log2(win + len(ch))))
    X = np.fft.rfft(ch, N)
    f = np.fft.rfftfreq(N, 1 / sr)
    bw = np.zeros_like(f)
    inb = (f >= band[0]) & (f <= band[1])
    bw[inb] = signal.windows.tukey(inb.sum(), 0.2)
    reg = 1e-3 * np.max(np.abs(X)) ** 2
    L = int(ir_len * sr) + int(0.004 * sr)
    # On real recordings the playback/record timeline is not rigid: chirps were found ~31 ms (1502 samples)
    # earlier than the sweep predicts. So locate every chirp directly with a matched filter (both mics summed,
    # search +-80 ms around the prediction) and window around the found arrival.
    mf = np.abs(signal.hilbert(signal.fftconvolve(mix, ch[::-1], mode="valid")))
    starts, found_off = [], []
    for s in ca[which]:
        lo = max(base + s - int(0.08 * sr), 0)
        k = lo + int(np.argmax(mf[lo: base + s + int(0.08 * sr)]))
        starts.append(k)
        found_off.append(k - (base + s))
    chirp_irs.last_offsets = found_off
    out, direct = [], []
    for chn in range(x.shape[1]):
        acc = np.zeros(L)
        for k in starts:
            seg = x[k - pre: k - pre + win, chn]
            acc += np.fft.irfft(np.fft.rfft(seg, N) * np.conj(X) / (np.abs(X) ** 2 + reg) * bw, N)[:L]
        a = signal.hilbert(signal.resample_poly(acc / len(ca[which]), UP, 1))
        out.append(a)
    out = np.array(out)
    for chn in range(out.shape[0]):
        direct.append(float(np.argmax(np.abs(out[chn, : int(0.006 * sr * UP)]))))
    return out, np.array(direct)


def rot(alpha_deg):
    a = np.deg2rad(alpha_deg)
    return np.array([[np.cos(a), np.sin(a)], [-np.sin(a), np.cos(a)]])


def load(sess, spots=None, source="sweep", anchor=None, band=None):
    man = json.load(open(os.path.join(sess, "session.json"), encoding="utf-8"))
    sr = man["plan"]["sr"]
    sw = man["plan"]["sweep"]
    sweep = log_sweep(sr, sw["f1"], sw["f2"], sw["T"])
    caps = [c for c in man["captures"] if spots is None or c["spot"] in spots]
    out = []
    for c in caps:
        _, x = wavfile.read(os.path.join(sess, c["file"].split("/")[-1]))
        if source == "sweep":
            irs, direct = impulse_responses(x.astype(np.float64), sweep, sr, ir_len=0.03, **({"band": band} if band else {}))
        else:
            irs, direct = chirp_irs(x.astype(np.float64), sweep, sr, man["plan"], source, **({"band": band} if band else {}))
        out.append([c, irs, direct])
    med = float(np.median([d[1] - d[0] for _, _, d in out]))
    if anchor is not None:
        # Back mic: its earliest arrival can be a through-the-body path or a reflection, so pin it to a fixed
        # offset from the bottom mic (measured on the sweep, airborne: ~16.5 samples).
        med = anchor * UP
        for _, irs, direct in out:
            direct[1] = direct[0] + med
    for _, irs, direct in ([] if anchor is not None else out):
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


def score(data, sr, offsets, phis, rhos, flip=False, mirror=False, mics_used=(0, 1), pivot=(0.0, 0.0)):
    fs = sr * UP
    P, R = np.meshgrid(np.deg2rad(phis), rhos, indexing="ij")
    N = np.stack([np.sin(P), np.cos(P)], -1)                 # wall normal, bearing clockwise from +y
    # pivot: phone-centre offset from the rotation axis, in the phone frame (lazy Susan orbit).
    mics = MICS * ([-1, 1] if mirror else [1, 1]) + np.asarray(pivot)
    spk = SPK * ([-1, 1] if mirror else [1, 1]) + np.asarray(pivot)
    H = np.zeros(P.shape)
    for c, irs, direct, yaw in data:
        Rk = rot(-yaw if flip else yaw)
        centre = np.asarray(offsets.get(c["spot"], (0.0, 0.0)))
        S = centre + Rk @ spk
        env = envelopes(irs, direct, sr)
        Sd = R - (N @ S)                                     # signed distance speaker -> wall
        Sp = S + 2 * Sd[..., None] * N                       # mirrored speaker
        for i in mics_used:
            Mw = centre + Rk @ mics[i]
            L = np.linalg.norm(Sp - Mw, axis=-1)
            d0 = np.linalg.norm(Mw - S)
            idx = direct[i] + (L - d0) / C * fs
            v = ndimage.map_coordinates(env[i], [idx.ravel()], order=1, mode="constant").reshape(idx.shape)
            H += v * L
    return H


def contrast(H):
    iso = np.median(H, axis=0)
    return ndimage.gaussian_filter1d(H - iso[None, :], 1.5, axis=1)


def find_pivot(data, sr, offsets, mics_used, rmax_pivot=0.30):
    """Search the phone-centre offset from the rotation axis (no measuring needed).
    Stage 1: cheap peakiness ranking on a coarse polar grid. Stage 2: the full rectangle (walls + corners) score
    on the best candidates, then local refinement with that score. (Peakiness alone was biased ~2-4 cm in sim;
    the rectangle score peaks at the true pivot.)"""
    phis = np.arange(0, 360, 2.0)
    rhos = np.arange(0.3, 5.0, 0.01)

    def Hc_of(pv):
        return contrast(score(data, sr, offsets, phis, rhos, mics_used=mics_used, pivot=pv))

    def peaky(pv):
        v = np.sort(Hc_of(pv).ravel())
        return float(v[-max(1, v.size // 500):].mean())

    def rect(pv):
        Hc = Hc_of(pv)
        # manhattan() indexes rows by integer degrees, so resample to 1-degree rows
        Hc1 = np.repeat(Hc, 2, axis=0)
        return manhattan(Hc1, np.arange(0, 360, 1.0), rhos, ncand=4)[0][0]
    cands = [(0.0, 0.0)] + [(r * np.sin(np.deg2rad(t)), r * np.cos(np.deg2rad(t)))
                            for r in np.arange(0.04, rmax_pivot + 1e-9, 0.04) for t in range(0, 360, 30)]
    ranked = sorted(((peaky(c), c) for c in cands), reverse=True)
    short = [c for _, c in ranked[:8]] + ([(0.0, 0.0)] if (0.0, 0.0) not in [c for _, c in ranked[:8]] else [])
    scored = sorted(((rect(c), c) for c in short), reverse=True)
    best_s, best = scored[0]
    for step in (0.02, 0.01, 0.005):
        for _ in range(3):
            local = [(best[0] + dx, best[1] + dy) for dx in (-step, 0, step) for dy in (-step, 0, step) if dx or dy]
            s2, c2 = max(((rect(c), c) for c in local))
            if s2 <= best_s:
                break
            best_s, best = s2, c2
    return best, scored[:5]


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


def run(sess, prefix, offsets, flip=False, mirror=False, spots=None, rmax=5.0, plot=True, source="sweep", mics_used=(0, 1),
        anchor=None, band=None, pivot=(0.0, 0.0)):
    man, sr, data, med = load(sess, spots, source, anchor, band)
    pivot_search = None
    if pivot == "auto":
        pivot, pivot_search = find_pivot(data, sr, offsets, mics_used)
    phis = np.arange(0, 360, 1.0)
    rhos = np.arange(0.3, rmax, 0.005)
    H = score(data, sr, offsets, phis, rhos, flip, mirror, mics_used, pivot)
    iso = np.median(H, axis=0)
    Hc = ndimage.gaussian_filter1d(H - iso[None, :], 1.5, axis=1)
    (s, p0, dists, strengths), allp = manhattan(Hc, phis, rhos)
    sharp = float((allp.max() - np.median(allp)) / (np.std(allp) + 1e-12))
    res = {"session": man.get("version"), "direct_offset_samples": round(med, 2), "flip_yaw": flip, "mirror_x": mirror,
           "pivot_m": [round(float(v), 3) for v in pivot],
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
    ap.add_argument("--source", default="sweep", choices=["sweep", "R", "L"], help="sweep = both speakers; R/L = that speaker's chirps only")
    ap.add_argument("--mics", default="1,2", help="1 = bottom mic, 2 = back mic")
    ap.add_argument("--pivot", default="0,0", help="phone-centre offset from the rotation axis (phone frame, m), or 'auto'")
    ap.add_argument("--anchor", type=float, default=None, help="pin back-mic direct to bottom-mic direct + this many samples (e.g. 16.5)")
    ap.add_argument("--band", default=None, help="IR band in Hz, e.g. 300,6000 (default sweep 300-16000, chirps 1000-16000)")
    a = ap.parse_args()
    offs = {i + 1: tuple(map(float, s.split(","))) for i, s in enumerate(a.offsets.split(";"))}
    spots = [int(s) for s in a.spots.split(",")] if a.spots else None
    r = run(a.sess, a.prefix, offs, a.flip_yaw, a.mirror_x, spots, a.rmax, source=a.source,
            mics_used=tuple(int(m) - 1 for m in a.mics.split(",")), anchor=a.anchor,
            band=tuple(float(v) for v in a.band.split(",")) if a.band else None,
            pivot="auto" if a.pivot == "auto" else tuple(float(v) for v in a.pivot.split(",")))
    m = r["manhattan"]
    print(json.dumps({"pivot": r["pivot_m"], "score": m["score"], "phi0": m["phi0_deg"], "walls": [(w["bearing_deg"], w["dist_m"]) for w in m["walls"]],
                      "room": m["room_size_m"], "sharp_sd": m["orientation_sharpness_sd"],
                      "truth": [(w["bearing_deg"], w["dist_m"]) for w in r.get("truth", {}).get("walls", [])]}))


if __name__ == "__main__":
    main()
