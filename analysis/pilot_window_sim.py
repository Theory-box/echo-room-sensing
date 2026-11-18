# Why do pilots under-read? Simulate the tones+pilots signal with a wall that moves 25 cm (known) at different speeds,
# run the same pilot tracker (2048-sample windows, hop 256), and compare with the truth.
import numpy as np, math, sys
SR, C, P, K0, NT, HOP = 48000, 343.0, 2048, 683, 256, 256
kk = K0 + np.arange(NT); piltones = [k for k in range(NT) if k % 16 == 8]
a = np.ones(NT)
for k in range(NT):
    e = min(k, NT - 1 - k); a[k] = 1 if e >= 16 else 0.2 + 0.8 * (0.5 - 0.5 * math.cos(math.pi * e / 16))
a[piltones] *= 2
rng = np.random.default_rng(0); ph = rng.uniform(0, 2 * np.pi, NT)

def synth(T, paths, noise=2e-5):
    """paths: list of (gain, distance(t) function in m, one-way). Each path = the periodic tone signal delayed by
    2*d/C (direct sound: d(t) ~ few cm). Computed per tone exactly (continuous delay)."""
    t = np.arange(int(T * SR)) / SR; x = np.zeros_like(t)
    for g, dfun in paths:
        tau = 2 * dfun(t) / C
        for k in range(NT):
            x += g * a[k] * np.cos(2 * np.pi * (kk[k] * SR / P) * (t - tau) + ph[k])
    return x + noise * rng.standard_normal(len(t))

def tracker(x, win=P, tones=None, tau_s=3.0):
    """pilot tracker as in the app; win = window length (must contain whole cycles of the tones used)"""
    tones = np.array(piltones if tones is None else tones); kabs = K0 + tones
    starts = np.arange(0, len(x) - win, HOP); n = np.arange(win)
    E = np.exp(-2j * np.pi * np.outer(kabs * SR / P, n) / SR)
    w = np.hanning(len(tones) + 2)[1:-1]; S = np.zeros(len(tones), complex); cum = 0; last = None; out = []
    fc = kabs.mean() * SR / P
    for i, s in enumerate(starts):
        b = (E @ x[s:s + win]) * np.exp(-2j * np.pi * kabs * SR / P * s / SR)
        al = max(HOP / (tau_s * SR), 1 / (i + 1)); S += al * (b - S)
        if i > 40:
            Dp = np.fft.ifft((b - S) * w, 64); Sp = np.fft.ifft(S * w, 64); d0 = int(np.argmax(np.abs(Sp)))
            cand = [m for m in range(64) if min((m - d0) % 64, (d0 - m) % 64) > 6]
            if last is not None:
                st = np.angle(Dp[cand] * np.conj(last[cand])); cum += -np.median(st) * C / (2 * np.pi * fc) / 2
            last = Dp
        out.append(cum)
    return (starts + win / 2) / SR, np.array(out)

def move(t0, dur, d0, dist):
    def f(t):
        u = np.clip((t - t0) / dur, 0, 1); return d0 - dist * (u - np.sin(2 * np.pi * u) / (2 * np.pi))   # smooth start/stop
    return f

if __name__ == '__main__':
    T = 14
    for dur in (8.0, 4.0, 2.0, 1.0):
        paths = [(1.0, lambda t: 0.02 + 0 * t), (0.05, lambda t: 0.84 + 0 * t), (0.012, move(4, dur, 1.0, 0.25))]
        x = synth(T, paths)
        peak = 2 * 0.25 / dur * 100
        for name, win in (('2048-sample window (app)', P), ('128-sample window', 128)):
            tt, cum = tracker(x, win=win)
            a0 = cum[(tt > 2) & (tt < 3.5)].mean(); b0 = cum[tt > tt[-1] - 1.5].mean()
            print(f'move 25 cm in {dur:.0f} s (peak {peak:.0f} cm/s), {name}: tracker {100*(b0-a0):+6.1f} cm  (truth -25.0)')
