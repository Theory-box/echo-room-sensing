"""Top-down reflector map from an Echo Room sweep session.

For every stop: deconvolve the log sweep to get a broadband impulse response (IR) per mic,
then back-project the two-mic cross term onto a horizontal grid around the phone, using
the phone's yaw at that stop. Reflectors that are consistent across rotations add up;
mirror ambiguities (a 2-mic array can't tell left from right of its axis) average out.

usage: python sweep_map.py <session_dir> <out_prefix>
"""
import json
import sys

import numpy as np
from scipy import signal
from scipy.io import wavfile

C = 343.0
UP = 4  # IR upsampling factor for sub-sample delays

# Phone frame (m), origin at the approximate rotation centre (phone centre), x right, y toward the top.
# Mic positions from Android MicrophoneInfo (bottom (2.69, 0.58), back (5.46, 14.56) cm),
# shifted by an assumed centre of (3.6, 7.7) cm. Speaker: bottom edge (assumed).
CENTRE = np.array([0.036, 0.077])
M = np.array([[0.0269, 0.0058], [0.0546, 0.1456]]) - CENTRE
S = np.array([0.040, 0.000]) - CENTRE


def log_sweep(sr, f1, f2, T):
    n = int(round(T * sr))
    t = np.arange(n) / sr
    K = np.log(f2 / f1)
    s = np.sin(2 * np.pi * f1 * T / K * (np.exp(t * K / T) - 1))
    fade = int(round(0.01 * sr))
    w = np.ones(n)
    r = 0.5 - 0.5 * np.cos(np.pi * np.arange(fade) / fade)
    w[:fade] = r
    w[-fade:] = r[::-1]
    return s * w


def impulse_responses(x, sweep, sr, band=(300.0, 16000.0), ir_len=0.06):
    """x: (n, ch). Returns analytic, upsampled IRs (ch, L) starting just before the direct path,
    plus the direct-path index per channel (in upsampled samples)."""
    mix = x.sum(axis=1)
    c = signal.fftconvolve(mix[: int(2.5 * sr)], sweep[::-1], mode="valid")
    start = int(np.argmax(np.abs(c))) - int(0.002 * sr)       # sweep start in recording (~direct path)
    seg = x[start: start + len(sweep) + int(0.3 * sr)]
    N = 1 << int(np.ceil(np.log2(len(seg) + len(sweep))))
    X = np.fft.rfft(sweep, N)
    f = np.fft.rfftfreq(N, 1 / sr)
    bw = np.zeros_like(f)
    inb = (f >= band[0]) & (f <= band[1])
    bw[inb] = signal.windows.tukey(inb.sum(), 0.2)
    reg = 1e-3 * np.max(np.abs(X)) ** 2
    out, direct = [], []
    L = int(ir_len * sr)
    for ch in range(x.shape[1]):
        Y = np.fft.rfft(seg[:, ch], N)
        h = np.fft.irfft(Y * np.conj(X) / (np.abs(X) ** 2 + reg) * bw, N)[: L + int(0.004 * sr)]
        h = signal.resample_poly(h, UP, 1)
        a = signal.hilbert(h)
        out.append(a)
    out = np.array(out)
    for ch in range(out.shape[0]):
        env = np.abs(out[ch, : int(0.006 * sr * UP)])
        direct.append(float(np.argmax(env)))
    return out, np.array(direct)


def backproject(irs, direct, alpha_deg, sr, X, Y, rmin=0.3):
    a = np.deg2rad(alpha_deg)
    # Phone rotated clockwise (seen from above) by alpha: room point -> phone frame.
    xp = X * np.cos(a) - Y * np.sin(a)
    yp = X * np.sin(a) + Y * np.cos(a)
    fs = sr * UP
    vals = []
    for i in range(2):
        rs = np.hypot(xp - S[0], yp - S[1])
        rm = np.hypot(xp - M[i][0], yp - M[i][1])
        d0 = np.hypot(*(M[i] - S))
        idx = direct[i] + (rs + rm - d0) / C * fs
        sig = irs[i] / (np.sqrt(np.mean(np.abs(irs[i][int(0.005 * fs):]) ** 2)) + 1e-12)
        k = np.clip(idx, 0, len(sig) - 2)
        k0 = np.floor(k).astype(int)
        t = k - k0
        v = sig[k0] * (1 - t) + sig[k0 + 1] * t
        v[idx > len(sig) - 2] = 0
        vals.append(v)
    r = np.hypot(X, Y)
    # Envelope product: needs both mics to see energy at their geometry-consistent delays, without the
    # carrier-phase fringes (14 cm spacing is many wavelengths at kHz). Spreading: amplitude ~1/r per mic.
    cross = np.abs(vals[0]) * np.abs(vals[1]) * r ** 2
    inc = (np.abs(vals[0]) + np.abs(vals[1])) * r
    cross[r < rmin] = 0
    inc[r < rmin] = 0
    return np.maximum(cross, 0), inc


def main(sess, out_prefix, extent=3.0, step=0.02):
    man = json.load(open(f"{sess}/session.json", encoding="utf-8"))
    sr = man["plan"]["sr"]
    sw = man["plan"]["sweep"]
    sweep = log_sweep(sr, sw["f1"], sw["f2"], sw["T"])
    g = np.arange(-extent, extent + step / 2, step)
    X, Y = np.meshgrid(g, g)
    spots = sorted({c["spot"] for c in man["captures"]})
    result = {"grid": g.tolist(), "spots": {}}
    # Pass 1: IRs for every capture. The mic-to-mic direct-path offset is fixed by the phone's geometry,
    # so take the median over all stops and re-pick the (weaker) back-mic direct peak near it.
    loaded = []
    for c in man["captures"]:
        _, x = wavfile.read(f"{sess}/{c['file'].split('/')[-1]}")
        irs, direct = impulse_responses(x.astype(np.float64), sweep, sr)
        loaded.append((c, irs, direct))
    med = float(np.median([d[1] - d[0] for _, _, d in loaded]))
    print(f"median direct-path offset mic2-mic1: {med / UP:.2f} samples")
    for _, irs, direct in loaded:
        lo, hi = int(direct[0] + med - 2 * UP), int(direct[0] + med + 2 * UP) + 1
        env = np.abs(irs[1][max(lo, 0):hi])
        direct[1] = max(lo, 0) + float(np.argmax(env)) if len(env) else direct[0] + med
    # Pass 2: align each IR so its direct path sits at a fixed index, then subtract the per-spot mean
    # over stops. Anything that doesn't change when the phone rotates (direct path, phone body, the stand,
    # and largely ceiling/floor) cancels; wall echoes move between stops and survive.
    D0 = int(0.003 * sr * UP)
    for i, (c, irs, direct) in enumerate(loaded):
        for ch in range(2):
            irs[ch] = np.roll(irs[ch], D0 - int(round(direct[ch])))
            irs[ch][: max(0, D0 - int(round(direct[ch])))] = 0
        direct[:] = D0
    for spot in spots:
        caps = [(c, irs, direct) for c, irs, direct in loaded if c["spot"] == spot]
        if len(caps) >= 4:
            mean = np.mean([irs for _, irs, _ in caps], axis=0)
            caps = [(c, irs - mean, direct) for c, irs, direct in caps]
        acc_c = np.zeros_like(X)
        acc_i = np.zeros_like(X)
        diag = []
        for c, irs, direct in caps:
            alpha = c["turnDir"] * c["yawStartDeg"] if c["turnDir"] else 0.0
            if c["stop"] > 1 and c["turnDir"] == 0:
                alpha = -c["yawStartDeg"]
            cr, inc = backproject(irs, direct, alpha, sr, X, Y)
            acc_c += cr
            acc_i += inc
            diag.append({"stop": c["stop"], "alpha": round(alpha, 1),
                         "direct_dt_samples": round((direct[1] - direct[0]) / UP, 2)})
        result["spots"][spot] = {"cross": acc_c, "inc": acc_i, "diag": diag}
        print(f"spot {spot}:", diag)
    np.savez_compressed(out_prefix + ".npz", grid=g,
                        **{f"cross{s}": result["spots"][s]["cross"] for s in spots},
                        **{f"inc{s}": result["spots"][s]["inc"] for s in spots})
    json.dump({str(s): result["spots"][s]["diag"] for s in spots}, open(out_prefix + "_diag.json", "w"), indent=1)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
