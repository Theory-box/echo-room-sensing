"""Simulate an Echo Room sweep in a rectangular room (image-source model) and write a session folder in
the app's format (WAV per stop + session.json), so the real analysis pipeline can run on it.

Frame: x right, y = the phone's top at the first stop (the session frame). Yaw is clockwise-positive,
seen from above with the screen up (the app's azimuth convention). The room is a rectangle rotated by
`room_rot` (deg, clockwise) about the session origin, with the phone centre at `phone` (m) inside it.

usage: python simulate.py <out_dir> [--room 3.6,4.4,2.5] [--phone 1.1,1.6,0.9] [--room-rot 20]
          [--stops 8] [--turn -1] [--spots 0,0] [--clutter N] [--noise -75] [--order 2]
          [--yaw-jitter 2] [--pos-jitter 0.01] [--seed 1]
  --phone: phone position relative to the room's corner (x along the room's width, y along its length, z height).
"""
import argparse
import json
import os

import numpy as np
from scipy import signal
from scipy.io import wavfile

C = 343.0
SR = 48000
# Phone frame (m, origin = phone centre), same as analysis/sweep_map.py.
CENTRE = np.array([0.036, 0.077])
MICS = np.array([[0.0269, 0.0058], [0.0546, 0.1456]]) - CENTRE
SPK = np.array([0.040, 0.000]) - CENTRE


def log_sweep(f1, f2, T):
    n = int(round(T * SR)); t = np.arange(n) / SR; K = np.log(f2 / f1)
    s = np.sin(2 * np.pi * f1 * T / K * (np.exp(t * K / T) - 1))
    fade = int(round(0.01 * SR)); w = np.ones(n); r = 0.5 - 0.5 * np.cos(np.pi * np.arange(fade) / fade)
    w[:fade] = r; w[-fade:] = r[::-1]
    return s * w


def lin_chirp(f0, f1, T, taper):
    n = int(round(T * SR)); i = np.arange(n); t = i / SR
    ph = 2 * np.pi * (f0 * t + (f1 - f0) * t * t / (2 * T))
    if taper == "hann":
        w = 0.5 - 0.5 * np.cos(2 * np.pi * i / (n - 1))
    else:
        r = 0.1 * n
        w = np.where(i < r, 0.5 - 0.5 * np.cos(np.pi * i / r),
                     np.where(i > n - 1 - r, 0.5 - 0.5 * np.cos(np.pi * (n - 1 - i) / r), 1.0))
    return w * np.cos(ph)


def plan():
    S = lambda x: int(round(x * SR))
    P = {"sr": SR, "A": 0.4, "total": S(4.9), "sweep": {"start": S(0.4), "f1": 50, "f2": 23500, "T": 1.5},
         "chirpA": {"f0": 1000, "f1": 18000, "T": 0.06, "L": [S(2.1), S(2.3)], "R": [S(2.5), S(2.7)]},
         "us": {"f0": 18000, "f1": 22000, "T": 0.04, "starts": [S(3.0) + k * S(0.21) for k in range(8)]},
         "preRollSamples": S(0.4), "channels": "ch1 = bottom mic, ch2 = back mic (simulated)"}
    play = np.zeros(P["total"])
    sw = log_sweep(50, 23500, 1.5); play[P["sweep"]["start"]:][:len(sw)] += 2 * P["A"] * sw  # both speakers
    ch = lin_chirp(1000, 18000, 0.06, "tukey")
    for s in P["chirpA"]["L"] + P["chirpA"]["R"]:
        play[s:s + len(ch)] += P["A"] * ch
    us = lin_chirp(18000, 22000, 0.04, "hann")
    for s in P["us"]["starts"]:
        play[s:s + len(us)] += 2 * P["A"] * us
    return P, play


def rot(alpha_deg):
    """Phone frame -> session frame for a phone turned clockwise by alpha."""
    a = np.deg2rad(alpha_deg)
    return np.array([[np.cos(a), np.sin(a)], [-np.sin(a), np.cos(a)]])


def add_tap(ir, delay_s, amp, half=32):
    d = delay_s * SR
    k0 = int(np.floor(d)); n = np.arange(k0 - half, k0 + half + 1)
    n = n[(n >= 0) & (n < len(ir))]
    ir[n] += amp * np.sinc(n - d) * (0.5 + 0.5 * np.cos(np.pi * (n - d) / (half + 1)))


def image_sources(src, walls, order):
    """walls: list of (n (2,), rho) lines n.x = rho in 2D. Returns [(image_pos, order)]."""
    out, frontier = [], [(src, -1, 0)]
    for o in range(1, order + 1):
        nxt = []
        for p, last, _ in frontier:
            for j, (n, rho) in enumerate(walls):
                if j == last:
                    continue
                q = p + 2 * (rho - n @ p) * n
                nxt.append((q, j, o)); out.append((q, o))
        frontier = nxt
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--room", default="3.6,4.4,2.5")
    ap.add_argument("--phone", default="1.1,1.6,0.9")
    ap.add_argument("--room-rot", type=float, default=20.0)
    ap.add_argument("--stops", type=int, default=8)
    ap.add_argument("--turn", type=int, default=-1)
    ap.add_argument("--spots", default="0,0", help="spot offsets in the session frame, e.g. '0,0;0.3,0'")
    ap.add_argument("--clutter", type=int, default=0)
    ap.add_argument("--noise", type=float, default=-75.0)
    ap.add_argument("--order", type=int, default=2)
    ap.add_argument("--beta", type=float, default=0.8)
    ap.add_argument("--yaw-jitter", type=float, default=2.0)
    ap.add_argument("--pos-jitter", type=float, default=0.01)
    ap.add_argument("--seed", type=int, default=1)
    a = ap.parse_args()
    rng = np.random.default_rng(a.seed)
    W, Lr, H = map(float, a.room.split(","))
    px, py, pz = map(float, a.phone.split(","))
    # Room corners in room coords, then into the session frame (phone centre at origin, room rotated).
    R0 = rot(a.room_rot)
    to_sess = lambda q: R0 @ (np.asarray(q) - np.array([px, py]))
    corners = [to_sess(c) for c in ([0, 0], [W, 0], [W, Lr], [0, Lr])]
    walls = []
    for i in range(4):
        p0, p1 = corners[i], corners[(i + 1) % 4]
        t = (p1 - p0) / np.linalg.norm(p1 - p0); n = np.array([t[1], -t[0]])
        rho = n @ p0
        if rho < 0:
            n, rho = -n, -rho
        walls.append((n, rho))
    truth = [{"bearing_deg": round(float(np.degrees(np.arctan2(n[0], n[1])) % 360), 1), "dist_m": round(float(r), 3)}
             for n, r in walls]
    clutter = []
    for _ in range(a.clutter):
        q = np.array([rng.uniform(0.2, W - 0.2), rng.uniform(0.2, Lr - 0.2)])
        if np.hypot(q[0] - px, q[1] - py) > 0.4:
            clutter.append((to_sess(q), rng.uniform(0.02, 0.08)))
    P, play = plan()
    spots = [np.array(list(map(float, s.split(",")))) for s in a.spots.split(";")]
    os.makedirs(a.out, exist_ok=True)
    b_lp, a_lp = signal.butter(1, 4000 / (SR / 2))   # back mic: weak above a few kHz (as measured)
    caps, latency = [], int(0.012 * SR)
    for si, off in enumerate(spots, 1):
        for k in range(a.stops):
            yaw = a.turn * k * 360 / a.stops + rng.normal(0, a.yaw_jitter) + 0.0
            centre = off + rng.normal(0, a.pos_jitter, 2)
            Rk = rot(yaw)
            S = centre + Rk @ SPK
            rec = []
            for mi in range(2):
                M = centre + Rk @ MICS[mi]
                ir = np.zeros(int(0.08 * SR))
                d0 = np.linalg.norm(M - S)
                add_tap(ir, d0 / C, 1.0 / max(d0, 0.05))
                for dp, amp in ((0.06, 3.0), (0.11, 2.0), (0.16, 1.2)):        # phone body / stand, phone-fixed
                    add_tap(ir, (d0 + dp) / C, amp)
                for q, o in image_sources(S, walls, a.order):
                    L = np.linalg.norm(M - q); add_tap(ir, L / C, a.beta ** o / L)
                for zimg in (2 * pz, 2 * (H - pz)):                               # floor / ceiling (first order)
                    L = np.hypot(np.linalg.norm(M - S), zimg); add_tap(ir, L / C, a.beta / L)
                for q, amp in clutter:
                    L = np.linalg.norm(q - S) + np.linalg.norm(q - M); add_tap(ir, L / C, amp / (np.linalg.norm(q - S) * np.linalg.norm(q - M)))
                y = signal.fftconvolve(play, ir)[: P["total"]] * 0.02
                if mi == 1:
                    y = signal.lfilter(b_lp, a_lp, y)
                full = np.zeros(P["preRollSamples"] + latency + P["total"] + int(0.8 * SR))
                full[P["preRollSamples"] + latency:][: len(y)] += y
                full += 10 ** (a.noise / 20) * rng.standard_normal(len(full))
                rec.append(full)
            x = np.stack(rec, 1).astype(np.float32)
            name = f"spot{si}_stop{k + 1:02d}.wav"
            wavfile.write(os.path.join(a.out, name), SR, x)
            caps.append({"spot": si, "stop": k + 1, "targetDeg": round(k * 360 / a.stops), "yawSessionDeg": round(yaw, 2),
                         "yawStartDeg": round(abs(yaw), 2), "turnDir": a.turn if k else 0, "file": "sim/" + name,
                         "spotOffsetTrue": [round(float(v), 3) for v in off]})
    man = {"version": "echo-room-sweep v2 (simulated)", "plan": {k: v for k, v in P.items()}, "captures": caps,
           "truth": {"room": [W, Lr, H], "phone": [px, py, pz], "roomRotDeg": a.room_rot, "walls": truth,
                     "ceiling_above_m": H - pz, "floor_below_m": pz, "clutter": len(clutter)},
           "yawConvention": "yawSessionDeg: signed, clockwise-positive, session frame"}
    json.dump(man, open(os.path.join(a.out, "session.json"), "w"), indent=1)
    print(json.dumps(man["truth"]))


if __name__ == "__main__":
    main()
